"""Day summary, rules and time entries (D-078)."""

import io
import json
import os
import shutil
import subprocess
from datetime import date, datetime, timedelta

import pytest

from app.core.schema.recap import EntryInput, EntryUpdate, TargetInput
from app.core.utils.actor import acting_as
from app.core.utils.history import batch, undo
from app.features.claude import mcp_server, mcp_time_tools, transcript_core
from app.features.recap import facts_core, kimai, recap_core

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
    monkeypatch.setattr(kimai, "entries", lambda day: [h for h in held if h["begin"].date() == day])
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
        "tasks": [],
        "asked": 0,
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


def test_claude_requests_are_counted_without_their_words(tmp_path, monkeypatch):
    monkeypatch.setattr(transcript_core, "projects_root", lambda: tmp_path)
    (tmp_path / "p").mkdir()
    start, end = facts_core.bounds(DAY)
    asked = {"type": "user", "cwd": "/w", "timestamp": (start + timedelta(hours=9)).isoformat()}
    lines = [
        {**asked, "message": {"content": "SECRET"}},
        {**asked, "message": {"content": [{"tool_use_id": "t"}]}},
        {**asked, "isMeta": True},
        {**asked, "timestamp": (end + timedelta(hours=1)).isoformat()},
    ]
    text = "\n".join([*(json.dumps(line, separators=(",", ":")) for line in lines), '{"type":"user" cut'])
    (tmp_path / "p" / "a.jsonl").write_text(text)
    assert {k: len(v) for k, v in facts_core._claude(start, end).items()} == {"/w": 1}


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
    assert half.minutes == 240  # the rest is the repository no rule places
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
