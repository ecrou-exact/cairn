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
    assert data["mode"] == "top" and data["breadcrumb"] == [{"label": "All projects", "url": "/graph"}]
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
    page = signed_in.get("/graph")
    assert page.status_code == 200 and b"data-graph-canvas" in page.data and b"style=" not in page.data
    csp = page.headers["Content-Security-Policy"]
    assert "style-src-attr 'unsafe-inline'" in csp and "script-src 'self'" in csp and "unsafe-eval" not in csp
    assert "style-src-attr" not in signed_in.get("/tasks").headers["Content-Security-Policy"]
    assert signed_in.get("/graph?project=nope").status_code == 404
    empty = signed_in.get("/api/graph").json
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
