import pytest

from app.core.schema.planning import DependencyCreate, ProjectCreate, TaskCreate
from app.features.graph import graph_core
from app.features.projects import projects_core
from app.features.tasks import dependencies_core, tasks_core

STEP = graph_core.CARD_W + graph_core.COL_GAP


def _task(title, **kw):
    return tasks_core.create(TaskCreate(title=title, **kw))


def _block(first, then, kind="blocks"):
    dependencies_core.add(DependencyCreate(from_task_id=first.id, to_task_id=then.id, kind=kind))


def _columns(data):
    return {n["data"]["label"]: int(n["x"] // STEP) for n in data["nodes"]}


def test_plan_reads_left_to_right(ctx):
    design = _task("Design", estimate_hours=4)
    build = _task("Build", estimate_hours=10)
    docs = _task("Docs", estimate_hours=1)
    ship = _task("Ship", estimate_hours=2)
    loose = _task("Loose end")
    _block(design, build)
    _block(build, ship)
    _block(docs, ship, kind="follows")
    data = graph_core.graph_data()
    assert data["mode"] == "top" and data["breadcrumb"] == [{"label": "All projects", "url": "/projects"}]
    col = _columns(data)
    assert col["Design"] == 0 and col["Build"] == 1 and col["Ship"] == 2
    assert col["Docs"] == 0 and col["Loose end"] == 0
    assert all(n["fx"] == n["x"] and n["fy"] == n["y"] for n in data["nodes"])  # pinned
    assert data["steps"] == 3
    assert data["critical"]["nodes"] == [str(design.id), str(build.id), str(ship.id)]
    assert data["critical"]["hours"] == 16.0
    edge = next(e for e in data["edges"] if e["from"] == str(design.id))
    assert edge["data"] == {"kind": "blocks", "note": "", "count": 1, "critical": True}
    assert loose.id


def test_parents_come_after_their_subtasks_which_inherit_blockers(ctx):
    before = _task("Phase 1")
    phase = _task("Phase 2")
    step = _task("Phase 2 step", parent_id=phase.id)
    _block(before, phase)
    col = _columns(graph_core.graph_data(level="all"))
    assert col["Phase 1"] < col["Phase 2 step"] < col["Phase 2"]
    kinds = {e["data"]["kind"] for e in graph_core.graph_data(level="all")["edges"]}
    assert kinds == {"blocks", "subtask"}
    assert step.id


def test_filters_and_cards(ctx):
    project = projects_core.create(ProjectCreate(name="Rulezet", color="moss"))
    _task("In project", project_id=project.id, due_on=None)
    done = _task("Done one", project_id=project.id)
    tasks_core.set_status(done.id, "done")
    _task("Elsewhere")
    only = graph_core.graph_data(project.id)
    assert [n["data"]["label"] for n in only["nodes"]] == ["In project"]
    card = only["nodes"][0]["data"]
    assert (card["project"], card["projectColor"], card["statusKind"], card["open"]) == (
        "Rulezet",
        "moss",
        "open",
        True,
    )
    assert len(graph_core.graph_data(project.id, include_closed=True)["nodes"]) == 2
    assert graph_core.graph_data()["critical"] == {"nodes": [], "hours": 0.0, "unknown": 0}


def test_graph_page_and_api(app, signed_in):
    root = signed_in.post("/api/tasks", json={"title": "A case"}).json["task"]["id"]
    page = signed_in.get(f"/graph?root={root}")
    assert page.status_code == 200 and b"data-graph-canvas" in page.data and b"style=" not in page.data
    csp = page.headers["Content-Security-Policy"]
    assert "style-src-attr 'unsafe-inline'" in csp and "script-src 'self'" in csp and "unsafe-eval" not in csp
    assert "style-src-attr" not in signed_in.get("/tasks").headers["Content-Security-Policy"]
    assert signed_in.get("/graph?project=nope").status_code == 404
    empty = signed_in.get("/api/graph?state=late").json  # the one task is not late
    assert (empty["nodes"], empty["edges"], empty["steps"], empty["mode"]) == ([], [], 0, "top")
    assert signed_in.get("/api/graph?project=x").status_code == 422


def test_levels_cases_subtasks_and_neighbourhood(ctx):
    project = projects_core.create(ProjectCreate(name="Cairn"))
    phase_a = _task("Phase A", project_id=project.id)
    phase_b = _task("Phase B", project_id=project.id)
    a1 = _task("A1", parent_id=phase_a.id, estimate_hours=3)
    a2 = _task("A2", parent_id=phase_a.id, estimate_hours=2)
    b1 = _task("B1", parent_id=phase_b.id)
    _block(a1, a2)
    _block(a2, b1)  # between subtasks of two cases: lifted to A -> B at the top level

    top = graph_core.graph_data(project.id)
    assert {n["data"]["label"] for n in top["nodes"]} == {"Phase A", "Phase B"}
    lifted = top["edges"][0]
    assert (lifted["from"], lifted["to"], lifted["data"]["count"]) == (str(phase_a.id), str(phase_b.id), 1)
    card = next(n["data"] for n in top["nodes"] if n["data"]["label"] == "Phase A")
    assert (card["children"], card["childrenDone"], card["drill"]) == (2, 0, f"/graph?root={phase_a.id}")
    assert top["critical"]["hours"] == 6.0  # A's 5 h of subtasks + B's unestimated subtask (1 h)

    inside = graph_core.graph_data(root_id=phase_a.id)
    assert inside["mode"] == "children"
    assert {n["data"]["label"] for n in inside["nodes"]} == {"A1", "A2"}
    assert [c["label"] for c in inside["breadcrumb"]] == ["All projects", "Cairn", "Phase A"]

    around = graph_core.graph_data(root_id=a2.id)
    assert around["mode"] == "around"
    assert {n["data"]["label"] for n in around["nodes"]} == {"A1", "A2", "B1"}
    assert next(n for n in around["nodes"] if n["data"]["isRoot"])["data"]["label"] == "A2"
    assert _columns(around) == {"A1": 0, "A2": 1, "B1": 2}


def test_cards_carry_the_workflow_moves(ctx):
    _task("Movable")
    card = graph_core.graph_data()["nodes"][0]["data"]
    keys = [move["key"] for move in card["next"]]
    assert "done" in keys and card["status"] not in keys
    assert all({"key", "label", "kind"} <= set(move) for move in card["next"])


def test_filters_keep_cases_leading_to_a_match(ctx):
    from datetime import date, timedelta

    phase = _task("Phase")
    _task("Late step", parent_id=phase.id, due_on=date.today() - timedelta(days=2), tags=["ops"])
    _task("Calm case")
    blocker = _task("Blocker")
    blocked = _task("Blocked one")
    _block(blocker, blocked)

    labels = lambda **kw: {n["data"]["label"] for n in graph_core.graph_data(**kw)["nodes"]}  # noqa: E731
    assert labels(state="late") == {"Phase"}  # kept: one of its subtasks is late
    assert labels(state="blocked") == {"Blocked one"}
    assert "Blocker" in labels(state="actionable") and "Blocked one" not in labels(state="actionable")
    assert labels(tag="ops") == {"Phase"} and labels(tag="#OPS") == {"Phase"}
    assert graph_core.tags_in_use() == ["ops"]


def test_graph_page_filters(app, signed_in):
    project = signed_in.post("/api/projects", json={"name": "Rulezet"}).json["project"]
    page = signed_in.get(f"/projects/{project['slug']}?tab=plan&state=late&tag=a+b")
    assert page.status_code == 200 and b"state=late" in page.data and b"tag=a+b" in page.data


def test_find_points_to_the_card_holding_the_task(ctx):
    project = projects_core.create(ProjectCreate(name="Cairn"))
    phase = _task("Phase graph", project_id=project.id)
    step = _task("Write the find box", parent_id=phase.id)
    deeper = _task("Find box keyboard", parent_id=step.id)
    done = _task("Find old notes")
    tasks_core.set_status(done.id, "done")
    _task("Late find", due_on=None, tags=["ops"])

    found = graph_core.find("  FIND   box ")
    assert found["query"] == "find box"
    by_label = {m["label"]: m for m in found["matches"]}
    assert set(by_label) == {"Write the find box", "Find box keyboard"}
    assert by_label["Write the find box"]["card"] == str(phase.id)
    assert by_label["Write the find box"]["inside"] == ["Phase graph"]
    assert by_label["Find box keyboard"]["inside"] == ["Phase graph", "Write the find box"]
    assert found["matches"][0]["label"] == "Write the find box"  # the shallower match first

    inside = graph_core.find("keyboard", root_id=phase.id)["matches"][0]
    assert (inside["card"], inside["inside"]) == (str(step.id), ["Write the find box"])
    assert graph_core.find("keyboard", level="all")["matches"][0]["card"] == str(deeper.id)

    assert graph_core.find("old notes")["matches"] == []  # done tasks only with closed=1
    assert graph_core.find("old notes", include_closed=True)["matches"][0]["card"] == str(done.id)
    filtered = graph_core.find("phase", tag="ops")["matches"][0]
    assert filtered["card"] is None  # in scope but filtered out: the page opens the task
    assert graph_core.find("find", limit=1)["more"] >= 2
    assert graph_core.find("   ") == {"query": "", "matches": [], "more": 0}


def test_find_api(app, signed_in):
    signed_in.post("/api/tasks", json={"title": "Searchable % card"})
    body = signed_in.get("/api/graph/find?q=%25").json
    assert [m["label"] for m in body["matches"]] == ["Searchable % card"]
    assert signed_in.get("/api/graph/find?q=x&root=nope").status_code == 422
    project = signed_in.post("/api/projects", json={"name": "Findable"}).json["project"]
    assert b'id="graph-find"' in signed_in.get(f"/projects/{project['slug']}").data


def test_graph_lives_in_the_projects(app, signed_in):
    project = signed_in.post("/api/projects", json={"name": "Vitrine"}).json["project"]
    assert signed_in.get("/graph").headers["Location"].endswith("/projects")
    to_project = signed_in.get(f"/graph?project={project['id']}").headers["Location"]
    assert to_project.endswith(f"/projects/{project['slug']}?tab=plan")
    shell = signed_in.get("/projects?mode=graph").data
    assert b'href="/graph"' not in shell and b"data-graph-canvas" in shell and b"view=projects" in shell
    plan = signed_in.get(f"/projects/{project['slug']}")
    assert b'aria-current="page"' in plan.data and b"cn-graph-toolbar" in plan.data
    assert "style-src-attr" in plan.headers["Content-Security-Policy"]
    listing = signed_in.get(f"/projects/{project['slug']}?q=x").data
    assert b'id="tasks"' in listing  # a list search lands on the tasks tab
    assert b"cn-project-about-grid" in signed_in.get(f"/projects/{project['slug']}?tab=about").data


def test_project_links_order_the_plan_of_projects(ctx):
    from app.core.schema.planning import ProjectLinkCreate
    from app.core.utils import history
    from app.features.projects import project_links_core

    rulezet = projects_core.create(ProjectCreate(name="Rulezet"))
    cairn = projects_core.create(ProjectCreate(name="Cairn"))
    vitrine = projects_core.create(ProjectCreate(name="Vitrine"))
    flow = projects_core.create(ProjectCreate(name="Flowintel"))
    project_links_core.add(ProjectLinkCreate(from_project_id=rulezet.id, to_project_id=cairn.id))
    project_links_core.add(ProjectLinkCreate(from_project_id=cairn.id, to_project_id=vitrine.id))
    # a task link across projects orders them too, shown with how many links it stands for
    _block(_task("Flow task", project_id=flow.id), _task("Vitrine task", project_id=vitrine.id))

    plan = graph_core.project_plan()
    assert plan["mode"] == "projects"
    col = {n["data"]["label"]: int(n["x"] // STEP) for n in plan["nodes"]}
    assert col["Rulezet"] == 0 and col["Cairn"] == 1 and col["Vitrine"] == 2 and col["Flowintel"] == 0
    kinds = sorted((e["data"]["kind"], e["data"]["count"]) for e in plan["edges"])
    assert kinds == [("before", 1), ("before", 1), ("follows", 1)]
    card = next(n["data"] for n in plan["nodes"] if n["data"]["label"] == "Vitrine")
    assert (card["kind"], card["open"], card["url"]) == ("project", 1, f"/projects/{vitrine.slug}")

    with pytest.raises(
        project_links_core.ProjectLinkError, match="cycle: “Vitrine” → “Rulezet” → “Cairn” → “Vitrine”"
    ):
        project_links_core.add(ProjectLinkCreate(from_project_id=vitrine.id, to_project_id=rulezet.id))
    with pytest.raises(project_links_core.ProjectLinkError, match="already"):
        project_links_core.add(ProjectLinkCreate(from_project_id=rulezet.id, to_project_id=cairn.id))
    with pytest.raises(project_links_core.ProjectLinkError, match="itself"):
        project_links_core.add(ProjectLinkCreate(from_project_id=cairn.id, to_project_id=cairn.id))

    around = project_links_core.for_project(cairn.id)
    assert [p.name for _, p in around["before"]] == ["Rulezet"] and [p.name for _, p in around["after"]] == [
        "Vitrine"
    ]

    link = around["before"][0][0]
    with history.batch() as batch_id:
        project_links_core.remove(link.id)
    assert project_links_core.for_project(cairn.id)["before"] == []
    history.undo(batch_id)
    assert [p.name for _, p in project_links_core.for_project(cairn.id)["before"]] == ["Rulezet"]


def test_project_links_api(app, signed_in):
    a = signed_in.post("/api/projects", json={"name": "First"}).json["project"]["id"]
    b = signed_in.post("/api/projects", json={"name": "Second"}).json["project"]["id"]
    made = signed_in.post("/api/project-links", json={"from_project_id": a, "to_project_id": b})
    assert made.status_code == 201
    back = signed_in.post("/api/project-links", json={"from_project_id": b, "to_project_id": a})
    assert back.status_code == 422 and "cycle" in back.json["error"]
    plan = signed_in.get("/api/graph?view=projects").json
    assert [e["data"]["kind"] for e in plan["edges"]] == ["before"]
    link = made.json["link"]["id"]
    assert signed_in.delete(f"/api/project-links/{link}").status_code == 200
    assert signed_in.delete(f"/api/project-links/{link}").status_code == 404
    assert signed_in.post("/api/project-links", json={"from_project_id": a}).status_code == 422
