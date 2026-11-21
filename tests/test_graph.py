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
    col = _columns(data)
    assert col["Design"] == 0 and col["Build"] == 1 and col["Ship"] == 2
    assert col["Docs"] == 0 and col["Loose end"] == 0
    assert all(n["fx"] == n["x"] and n["fy"] == n["y"] for n in data["nodes"])  # pinned
    assert data["steps"] == 3
    assert data["critical"]["nodes"] == [str(design.id), str(build.id), str(ship.id)]
    assert data["critical"]["hours"] == 16.0
    edge = next(e for e in data["edges"] if e["from"] == str(design.id))
    assert edge["data"] == {"kind": "blocks", "note": "", "critical": True}
    assert loose.id


def test_parents_come_after_their_subtasks_which_inherit_blockers(ctx):
    before = _task("Phase 1")
    phase = _task("Phase 2")
    step = _task("Phase 2 step", parent_id=phase.id)
    _block(before, phase)
    col = _columns(graph_core.graph_data())
    assert col["Phase 1"] < col["Phase 2 step"] < col["Phase 2"]
    kinds = {e["data"]["kind"] for e in graph_core.graph_data()["edges"]}
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
    assert page.status_code == 200 and b'id="graph-canvas"' in page.data and b"style=" not in page.data
    csp = page.headers["Content-Security-Policy"]
    assert "style-src-attr 'unsafe-inline'" in csp and "script-src 'self'" in csp and "unsafe-eval" not in csp
    assert "style-src-attr" not in signed_in.get("/tasks").headers["Content-Security-Policy"]
    assert signed_in.get("/graph?project=nope").status_code == 404
    assert signed_in.get("/api/graph").json == {
        "nodes": [], "edges": [], "critical": {"nodes": [], "hours": 0.0, "unknown": 0}, "steps": 0,
    }  # fmt: skip
    assert signed_in.get("/api/graph?project=x").status_code == 422
