"""Day summary, rules and time entries (D-078)."""

import io
import os
import shutil
import subprocess
from datetime import date, datetime, timedelta

import pytest

from app.core.db_class.planning import Project
from app.core.extensions import db
from app.core.schema.recap import EntryInput, EntryUpdate, TargetInput
from app.core.utils.actor import acting_as
from app.core.utils.history import batch, undo
from app.core.utils.settings import set_setting
from app.features.claude import mcp_server, mcp_time_tools
from app.features.recap import facts_core, kimai, period_core, recap_core

DAY = date(2026, 11, 20)
CATALOG = [
    {
        "id": 7,
        "name": "ALPHA",
        "customer": "EU",
        "activities": [{"id": 70, "name": "T1"}, {"id": 71, "name": "T2"}],
    }
]
TOKEN = "kimai-secret-token"


@pytest.fixture()
def tracking(monkeypatch):
    """A Kimai that keeps what it is sent."""
    monkeypatch.setenv("CAIRN_KIMAI_URL", "https://time.example")
    monkeypatch.setenv("CAIRN_KIMAI_TOKEN", TOKEN)
    monkeypatch.setattr(kimai, "catalog", lambda: CATALOG)
    held = []

    def create(begin, minutes, project, activity, description, tags):
        held.append(
            {
                "id": 100 + len(held), "begin": begin, "end": begin + timedelta(minutes=minutes),
                "minutes": minutes, "project": project, "activity": activity, "tags": tags,
                "project_name": "ALPHA", "activity_name": "T", "description": description,
            }
        )  # fmt: skip
        return held[-1]["id"]

    monkeypatch.setattr(kimai, "create", create)
    monkeypatch.setattr(
        kimai,
        "entries",
        lambda day, last=None: [h for h in held if day <= h["begin"].date() <= (last or day)],
    )
    return held


def _rule(label="Tool", activity=70, **more):
    return recap_core.save_target(
        TargetInput(
            label=label, kimai_project=7, kimai_activity=activity, **{"repos": ["Org/Tool.git"], **more}
        )
    )


def _commit(subject, hour, branch="main"):
    at = datetime(2026, 11, 20, hour, 5).astimezone().isoformat()
    return {"sha": subject[:9], "at": at, "branch": branch, "subject": subject, "url": f"https://x/{subject}"}


def _facts(*commits, name="tool", slots=()):
    row = {
        "name": name,
        "repo": f"org/{name}",
        "commits": list(commits),
        "items": [],
    }
    return {"repos": [{**row, "slots": list(slots)}], "github": True, "folders": 1}


def test_git_is_read_on_every_branch_once(tmp_path, monkeypatch):
    git = shutil.which("git")
    home = tmp_path / "home"
    home.mkdir()
    for name in ("HOME", "XDG_CONFIG_HOME"):
        monkeypatch.setenv(name, str(home))
    when = "2026-11-20T10:05:00"

    def run(folder, *args, author="me"):
        env = {"GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when, "GIT_AUTHOR_NAME": author}
        env |= {"GIT_AUTHOR_EMAIL": f"{author}@x", "GIT_COMMITTER_NAME": "c", "GIT_COMMITTER_EMAIL": "c@x"}
        subprocess.run(  # noqa: S603
            [git, "-C", str(folder), *args], check=True, capture_output=True, env={**os.environ, **env}
        )

    repo = tmp_path / "work" / "tool"
    repo.mkdir(parents=True)
    run(repo, "init", "-q", "-b", "main")
    run(repo, "config", "user.name", "me")
    run(repo, "remote", "add", "origin", "git@github.com:Org/Tool.git")
    run(repo, "commit", "--allow-empty", "-m", "first")
    run(repo, "commit", "--allow-empty", "-m", "not mine", author="other")
    run(repo, "switch", "-q", "-c", "feature/x")
    run(repo, "commit", "--allow-empty", "-m", "second")
    start, end = facts_core.bounds(DAY)
    found = {}
    facts_core._walk(tmp_path, 3, found)
    assert list(found) == [repo.resolve()]
    read = facts_core._read_repository(repo, start, end, "")
    assert read["repo"] == "Org/Tool"
    assert {(c["subject"], c["branch"]) for c in read["commits"]} >= {("second", "feature/x")}
    assert sorted(c["subject"] for c in read["commits"]) == ["first", "second"]
    row = {"name": "tool", "commits": [], "slots": set()}
    seen, same = set(), set()
    for commit in (*read["commits"], *read["commits"], {**read["commits"][0], "sha": "rebased"}):
        facts_core._add(row, commit, "Org/Tool", seen, same)
    assert len(row["commits"]) == 2 and len(row["slots"]) == 1


def test_a_span_is_read_once_and_split_by_day(monkeypatch):
    """Git and GitHub are read once for a period; Claude's conversations are never read (D-103)."""
    first, last = DAY - timedelta(days=1), DAY
    calls = []
    monkeypatch.setattr(facts_core, "repositories", lambda: ["/r"])

    def github(start, end):
        calls.append((start, end))
        at = datetime(2026, 11, 19, 16).astimezone().isoformat()
        item = {"kind": "pr_merged", "repo": "org/tool", "number": 4, "title": "t", "url": "u", "at": at}
        return {"login": "me", "read": True, "items": [item], "commits": []}

    commits = [
        _commit("monday", 9),
        {**_commit("sunday", 9), "at": datetime(2026, 11, 19, 9).astimezone().isoformat()},
    ]
    monkeypatch.setattr(facts_core, "_github", github)
    monkeypatch.setattr(
        facts_core, "_read_repository", lambda *a: {"repo": "Org/Tool", "github": True, "commits": commits}
    )
    found = facts_core.gather_span(first, last)
    assert len(calls) == 1 and list(found) == [first, last]
    (before,), (after,) = found[first]["repos"], found[last]["repos"]
    assert [c["subject"] for c in before["commits"]] == ["sunday"] and len(before["items"]) == 1
    assert [c["subject"] for c in after["commits"]] == ["monday"] and after["items"] == []
    assert after["commits"][0]["url"].startswith("https://github.com/Org/Tool/commit/")
    assert not hasattr(facts_core, "_claude")


def test_rules_place_the_work(ctx, tracking):
    main = _rule(is_default=True)
    study = _rule("Study", 71, keywords=["Phishing"])
    everywhere = _rule("Talks", 71, repos=[], keywords=["slides"])
    rules = recap_core.targets()
    assert main.repos == ["tool"]
    assert recap_core.target_for("tool", "a fix", rules) is main
    assert recap_core.target_for("tool", "new PHISHING view", rules) is study
    assert recap_core.target_for("else", "slides for Monday", rules) is everywhere
    assert recap_core.target_for("else", "a fix", rules) is None
    with pytest.raises(kimai.KimaiError):
        _rule("Wrong", 99)
    with pytest.raises(ValueError):
        TargetInput(label="Empty", kimai_project=7, kimai_activity=70)
    found, lost = recap_core.plan(_facts(_commit("fix", 9), _commit("phishing", 10)), rules)
    assert {t.label for t, _, _ in found} == {"Tool", "Study"} and lost == {}
    assert recap_core.plan(_facts(_commit("fix", 9), name="mine"), rules) == ([], {"mine": 1})
    assert [t.label for t in recap_core.targets("phish")] == [] and len(recap_core.targets("tool")) == 2
    assert recap_core.share([3, 1], 480) == [360, 120]
    assert sum(recap_core.share([7, 5, 3], 480)) == 480


def test_drafts_then_the_owner_sends_once(ctx, tracking, monkeypatch):
    rule = _rule(tags=["dev"], about="Development")
    monkeypatch.setattr(facts_core, "gather", lambda day: _facts(_commit("new view", 9), slots=["09:00"]))
    with pytest.raises(recap_core.RecapError):
        recap_core.propose(DAY)
    found = recap_core.read_day(DAY)
    assert "new view" in found.summary_md
    recap_core.save_summary(DAY, "mine")
    assert recap_core.read_day(DAY).summary_md == "mine"
    (draft,) = recap_core.propose(DAY)
    assert (draft.begin, draft.minutes) == ("08:00", 480) and draft.description.startswith(
        "Development\ntool (main)"
    )
    assert tracking == []  # nothing is sent by proposing
    facts = _facts(_commit("a", 9), slots=["09:00"])
    facts["repos"] += _facts(_commit("b", 9), name="mine", slots=["09:00"])["repos"]
    monkeypatch.setattr(facts_core, "gather", lambda day: facts)
    recap_core.read_day(DAY - timedelta(days=1))
    (half,) = recap_core.propose(DAY - timedelta(days=1))
    assert half.minutes == 480  # the whole day: work no rule places takes nothing
    with pytest.raises(recap_core.RecapError):
        recap_core.propose(DAY)
    recap_core.update_entry(draft.id, EntryUpdate(minutes=240))
    second = recap_core.add_entry(
        DAY, EntryInput(target_id=rule.id, begin="11:00", minutes=60, description="x")
    )
    with pytest.raises(recap_core.RecapError, match="overlaps"):
        recap_core.send(DAY, [draft.id, second.id])
    assert tracking == []
    with batch() as batch_id:
        recap_core.delete_entry(second.id)
    undo(batch_id)
    recap_core.update_entry(second.id, EntryUpdate(begin="13:00"))
    with acting_as("claude:x"), pytest.raises(recap_core.RecapError, match="owner"):
        recap_core.send(DAY, [draft.id])
    recap_core.send(DAY, [draft.id, second.id])
    assert [(h["minutes"], h["activity"], h["tags"]) for h in tracking] == [
        (240, 70, ["dev"]),
        (60, 70, ["dev"]),
    ]
    for again in (lambda: recap_core.send(DAY, [draft.id]), lambda: recap_core.delete_entry(draft.id)):
        with pytest.raises(recap_core.RecapError):
            again()
    draft.sent_at = draft.kimai_id = None  # its answer was lost: it is found, not created twice
    recap_core.send(DAY, [draft.id])
    assert draft.kimai_id == 100 and len(tracking) == 2
    with pytest.raises(recap_core.RecapError):
        recap_core.read_day(date.today() + timedelta(days=1))


def test_a_day_already_full_in_kimai_is_left_alone(ctx, tracking, monkeypatch):
    _rule()
    kimai.create(datetime(2026, 11, 20, 9), 480, 1, 1, "Absent", [])
    monkeypatch.setattr(facts_core, "gather", lambda day: _facts(_commit("x", 9)))
    recap_core.read_day(DAY)
    with pytest.raises(recap_core.RecapError, match="full day"):
        recap_core.propose(DAY)


def test_pages_and_api(app, signed_in, tracking, monkeypatch):
    monkeypatch.setattr(facts_core, "gather", lambda day: _facts(_commit("new <b>view</b>", 9)))
    assert signed_in.get("/day").status_code == 302 and signed_in.get("/day/nope").status_code == 404
    page = signed_in.get("/day/rules")
    assert b"ALPHA: T1" in page.data
    form = {"label": "Tool", "repos": "org/tool", "place": "7:70", "guidance": "the tool"}
    assert b"Rule added" in signed_in.post("/day/rules", data=form, follow_redirects=True).data
    rule = signed_in.get("/api/time-rules").json["rules"][0]
    assert rule["activity_label"] == "T1" and b"the tool" in signed_in.get("/day/rules?q=tool").data
    assert b"Save the rule" in signed_in.get(f"/day/rules?edit={rule['id']}").data
    exported = signed_in.get("/day/rules/export").data
    assert TOKEN.encode() not in exported and b"time.example" not in exported
    sent = {"file": (io.BytesIO(exported), "rules.json")}
    assert b"Rules imported" in signed_in.post("/day/rules/import", data=sent, follow_redirects=True).data
    assert len(signed_in.get("/api/time-rules").json["rules"]) == 1
    assert signed_in.post("/api/time-rules", json={"label": "x"}).status_code == 422
    url = f"/day/{DAY}"
    assert b"was read" in signed_in.post(f"{url}/read", follow_redirects=True).data
    page = signed_in.post(f"{url}/propose", follow_redirects=True).data
    assert b"Send 1 to Kimai" in page and b"<b>view" not in page and TOKEN.encode() not in page
    entry = signed_in.get(f"/api{url}").json["entries"][0]
    data = {"target_id": entry["target_id"], "begin": "09:00", "duration": "7:30", "description": "done"}
    signed_in.post(f"{url}/entries/{entry['id']}", data=data)
    assert signed_in.get(f"/api{url}").json["entries"][0]["minutes"] == 450
    assert (
        b"hours:minutes"
        in signed_in.post(f"{url}/entries", data={**data, "duration": "x"}, follow_redirects=True).data
    )
    assert tracking == []
    assert (
        b"Sent to Kimai"
        in signed_in.post(f"{url}/send", data={"entries": entry["id"]}, follow_redirects=True).data
    )
    assert len(tracking) == 1
    assert signed_in.post(f"/api{url}/send", json={"entries": [entry["id"]]}).status_code == 409


def test_the_token_stays_home(monkeypatch):
    monkeypatch.setenv("CAIRN_KIMAI_URL", "http://time.example")
    monkeypatch.setenv("CAIRN_KIMAI_TOKEN", TOKEN)
    assert not kimai.configured()  # never in clear
    with pytest.raises(kimai.KimaiError) as refused:
        kimai.entries(DAY)
    assert TOKEN not in str(refused.value)
    assert kimai._NoRedirect().redirect_request() is None


def test_claude_cannot_send():
    tools = (*mcp_server.READ_TOOLS, *mcp_server.WRITE_TOOLS, *mcp_server.PROPOSAL_TOOLS)
    assert set(mcp_time_tools.WRITE_TOOLS) <= set(mcp_server.WRITE_TOOLS)
    assert not [name for name in tools if "send" in name]


def test_the_day_is_shared_equally():
    assert recap_core.share([1], 480) == [480]
    assert recap_core.share([1, 1], 480) == [240, 240]
    assert sorted(recap_core.share([1, 1, 1], 480)) == [150, 165, 165]


def test_weekends_and_days_off_are_never_filled(ctx, tracking, monkeypatch):
    _rule()
    saturday = date(2026, 11, 21)
    monkeypatch.setattr(facts_core, "gather", lambda day: _facts(_commit("x", 9)))
    assert recap_core.day_off(saturday) == "weekend" and recap_core.day_off(DAY) == ""
    recap_core.read_day(saturday)
    with pytest.raises(recap_core.RecapError, match="weekend"):
        recap_core.propose(saturday)
    set_setting("recap.days_off", ["2026-11-18..2026-11-20"])
    assert recap_core.day_off(DAY) == "day off" and recap_core.day_off(DAY + timedelta(days=3)) == ""
    with pytest.raises(ValueError):
        set_setting("recap.days_off", ["Christmas"])


def test_a_period_is_filled_by_day_and_sent_by_rule(ctx, tracking, monkeypatch):
    """Mon 16 to Sun 22 Nov 2026, Wednesday off: each working day split equally between the rules of
    its work; only the ticked rule is sent."""
    tool = _rule()
    other = _rule("Other", 71, repos=["other"])
    set_setting("recap.days_off", ["2026-11-18"])
    first, last = date(2026, 11, 16), date(2026, 11, 22)

    def span(a, b):
        found = {}
        for n in range((b - a).days + 1):
            day = a + timedelta(days=n)
            facts = _facts(_commit(f"tool {day}", 9))
            if day.day in (16, 21):  # Monday, and a Saturday
                facts["repos"] += _facts(_commit("other", 10), name="other")["repos"]
            found[day] = facts
        return found

    monkeypatch.setattr(facts_core, "gather_span", span)
    with pytest.raises(recap_core.RecapError):
        period_core.read_period(last, first)
    assert period_core.read_period(first, last) == 7
    done = period_core.propose_period(first, last)
    assert done["made"] == ["2026-11-16", "2026-11-17", "2026-11-19", "2026-11-20"]
    monday = sorted((e.target_id, e.minutes) for e in recap_core.entries(first))
    assert monday == sorted([(tool.id, 240), (other.id, 240)])
    assert recap_core.entries(date(2026, 11, 18)) == recap_core.entries(date(2026, 11, 21)) == []
    found = period_core.describe_period(first, last)
    assert {r["target"]: r["draft"] for r in found["rules"]} == {"Tool": 480 * 3 + 240, "Other": 240}
    assert "[`tool 2026`](https://x/tool 2026-11-16)" in found["summary"]
    assert "Claude" not in found["summary"]
    with acting_as("claude:x"), pytest.raises(recap_core.RecapError, match="owner"):
        period_core.send_period(first, last, [other.id])
    assert period_core.send_period(first, last, [other.id]) == 1
    assert [(h["activity"], h["minutes"]) for h in tracking] == [(71, 240)]
    with pytest.raises(recap_core.RecapError, match="No draft"):
        period_core.send_period(first, last, [other.id])
    assert period_core.propose_period(first, last)["made"] == []  # days with entries are left


def _project(slug, repo):
    db.session.add(Project(name=slug, slug=slug, github_repo=repo))
    db.session.commit()


def test_only_the_chosen_projects_are_seen_and_a_try_creates_nothing(app, signed_in, tracking, monkeypatch):
    facts = _facts(_commit("new view", 9))
    facts["repos"] += _facts(_commit("mine", 10), name="cairn")["repos"]
    monkeypatch.setattr(facts_core, "gather_span", lambda a, b: {DAY: facts})
    with app.app_context():
        _rule(tags=["dev"])
        _project("tool", "org/tool")
        _project("cairn", "me/cairn")
    picks = {p["slug"]: p for p in signed_in.get("/api/period-projects").json["projects"]}
    assert picks["tool"]["chosen"] and not picks["cairn"]["rules"] and not picks["cairn"]["chosen"]
    url = f"/api/period/{DAY}/{DAY}"
    assert signed_in.post(f"{url}/try", json={"projects": []}).status_code == 422
    assert signed_in.post(f"{url}/try", json={"projects": ["cairn"]}).status_code == 409
    (week,) = signed_in.post(f"{url}/try", json={"projects": ["tool"]}).json["weeks"]
    (block,) = week[4]["blocks"]
    assert block["trial"] and block["minutes"] == 480 and block["tags"] == ["dev"]
    assert (block["customer"], block["project"], block["activity"]) == ("EU", "ALPHA", "T1")
    found = signed_in.get(url).json
    assert found["days"][0]["entries"] == [] and tracking == []
    assert [r["name"] for r in found["days"][0]["facts"]["repos"]] == ["tool"]
    assert found["days"][0]["unplaced"] == [] and "cairn" not in found["summary"]
    assert "cairn" not in signed_in.get(f"/api/day/{DAY}").json["summary"]
    for view in ("calendar", "list"):
        page = signed_in.get(f"/day/period?from={DAY}&to={DAY}&view={view}").data
        assert b"ALPHA" in page and b"Create the drafts (8:00)" in page and b"data-rule" not in page
    signed_in.post(f"{url}/propose")
    (week,) = signed_in.get(f"{url}/preview").json["weeks"]
    assert [b["trial"] for b in week[4]["blocks"]] == [False]  # the same, now a draft


def test_period_page_and_api(app, signed_in, tracking, monkeypatch):
    monkeypatch.setattr(facts_core, "gather_span", lambda a, b: {a: _facts(_commit("x", 9))})
    with app.app_context():
        _rule()
        _project("tool", "org/tool")
    page = signed_in.get(f"/day/period?from={DAY}&to={DAY}")
    assert page.status_code == 200 and b'value="tool"' in page.data and b'id="preview"' not in page.data
    form = {"from": DAY.isoformat(), "to": DAY.isoformat()}
    tried = signed_in.post("/day/period/try", data={**form, "projects": "tool"}, follow_redirects=True)
    assert b"1 day read" in tried.data
    assert b"ends before" in signed_in.get(f"/day/period?from={DAY}&to={DAY - timedelta(days=1)}").data
    assert signed_in.get(f"/api/period/{DAY}/{DAY}").json["days"][0]["read"]
    assert signed_in.post(f"/api/period/{DAY}/{DAY}/send", json={"rules": []}).status_code == 422


def test_a_period_says_what_kimai_or_github_did_not_give(ctx, tracking, monkeypatch):
    _rule()

    def refused(day, last=None):
        raise kimai.KimaiError("no answer")

    facts = {**_facts(_commit("x", 9)), "github": False}
    monkeypatch.setattr(facts_core, "gather_span", lambda a, b: {DAY: facts})
    monkeypatch.setattr(kimai, "entries", refused)
    period_core.read_period(DAY, DAY)
    done = period_core.propose_period(DAY, DAY)
    assert done["made"] == [] and "no answer" in done["left"][0] and recap_core.entries(DAY) == []
    assert not period_core.describe_period(DAY, DAY)["github"]


def _hub(dates, calls):
    """GitHub's search over commits of these dates: 100 by page, 1000 at most."""

    def gh(path, *fields):
        if path == "user":
            return {"login": "me"}
        asked = dict(f.split("=", 1) for f in fields)
        if path != "search/commits":
            return {"total_count": 0, "items": []}
        calls.append(asked)
        first, _, last = asked["q"].split("author-date:")[1].partition("..")
        kept = [d for d in dates if datetime.fromisoformat(first) <= d <= datetime.fromisoformat(last)]
        page = int(asked.get("page", 1))
        rows = [
            {
                "sha": f"{d:%d}{n}",
                "repository": {"full_name": "org/tool"},
                "commit": {"author": {"date": d.isoformat()}, "message": "x"},
            }
            for n, d in enumerate(kept)
        ]
        return {"total_count": len(kept), "items": rows[:1000][(page - 1) * 100 : page * 100]}

    return gh


def test_every_page_of_github_is_read(monkeypatch):
    start, end = facts_core.bounds(date(2026, 11, 1))[0], facts_core.bounds(date(2026, 11, 20))[1]
    calls = []
    month = [start + timedelta(minutes=50 * n) for n in range(524)]
    monkeypatch.setattr(facts_core.programs, "gh", _hub(month, calls))
    found = facts_core._github(start, end)
    assert found["read"] and len(found["commits"]) == 524 and len(calls) == 6
    many = [start + timedelta(minutes=20 * n) for n in range(1400)]  # more than one search gives
    monkeypatch.setattr(facts_core.programs, "gh", _hub(many, calls))
    found = facts_core._github(start, end)
    assert found["read"] and len(found["commits"]) == 1400
    assert len({c["at"] for c in found["commits"]}) == 1400


def test_a_page_github_does_not_give_is_said(monkeypatch):
    start, end = facts_core.bounds(DAY)
    whole = _hub([start + timedelta(minutes=n) for n in range(150)], [])
    monkeypatch.setattr(
        facts_core.programs, "gh", lambda path, *f: None if "page=2" in f else whole(path, *f)
    )
    found = facts_core._github(start, end)
    assert not found["read"] and len(found["commits"]) == 100


def test_a_day_of_many_commits_names_a_few(ctx, tracking, monkeypatch):
    rule = _rule()
    facts = _facts(
        _commit("same", 9), *(_commit(f"c{n}", 9, f"b{n}") for n in range(300)), _commit("same", 9)
    )
    monkeypatch.setattr(facts_core, "gather_span", lambda a, b: {DAY: facts})
    period_core.read_period(DAY, DAY)
    ((_, _, text),), _ = recap_core.plan(facts, [rule])
    period = period_core.describe_period(DAY, DAY)["summary"]
    for said in (text, recap_core.get_day(DAY).summary_md, period):
        assert "and 296 more commits" in said and "c4" in said and "c5" not in said
        assert said.count("https://x/same") == 1


def test_the_preview_shows_kimai_and_what_is_wrong(app, signed_in, tracking, monkeypatch):
    first, last = DAY - timedelta(days=1), date(2026, 11, 22)  # Thursday to Sunday
    monkeypatch.setattr(facts_core, "gather_span", lambda a, b: {DAY: _facts(_commit("x", 9))})
    with app.app_context():
        _rule()
    signed_in.post(f"/api/period/{first}/{last}/read")
    signed_in.post(f"/api/period/{first}/{last}/propose")
    (week,) = signed_in.get(f"/api/period/{first}/{last}/preview").json["weeks"]
    assert week[:3] == [None] * 3 and week[3]["problems"] == ["not read"]
    assert week[4]["minutes"] == 480 and week[4]["problems"] == [] and week[5]["off"] == "weekend"
    kimai.create(datetime(2026, 11, 20, 9), 60, 1, 1, "Meeting", [])
    (week,) = signed_in.get(f"/api/period/{first}/{last}/preview").json["weeks"]
    assert len(week[4]["blocks"]) == 2
    assert week[4]["problems"] == ["entries overlap", "more than a day"]
    page = signed_in.get(f"/day/period?from={first}&to={last}").data
    assert b"entries overlap" in page and b"data-rule" in page and len(tracking) == 1
