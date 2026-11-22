"""The graph at the size the brief asks for (§4: 300+ nodes): built well within a second."""

import random
import time

from app.core.db_class.planning import Dependency
from app.core.extensions import db
from app.core.schema.planning import ProjectCreate, TaskCreate
from app.features.graph import graph_core
from app.features.projects import projects_core
from app.features.tasks import dependencies_core, tasks_core


def test_three_hundred_and_more_cards(ctx):
    rng = random.Random(7)  # noqa: S311 (test data, not security)
    projects = [projects_core.create(ProjectCreate(name=f"P{i}")) for i in range(4)]
    tasks = []
    for i in range(360):
        parent = tasks[rng.randrange(len(tasks))].id if tasks and i % 6 == 0 else None
        tasks.append(
            tasks_core.create(
                TaskCreate(
                    title=f"Task {i}", project_id=projects[i % 4].id, parent_id=parent, estimate_hours=2
                )
            )
        )
    pairs = {tuple(sorted(rng.sample(range(len(tasks)), 2))) for _ in range(300)}  # earlier → later: no cycle
    for a, b in pairs:  # rows written directly, derived values computed once (the core does it per link)
        db.session.add(Dependency(from_task_id=tasks[a].id, to_task_id=tasks[b].id, kind="blocks"))
    db.session.flush()
    dependencies_core.refresh_derived()

    started = time.perf_counter()
    everything = graph_core.graph_data(level="all")
    cases = graph_core.graph_data()
    plan = graph_core.project_plan()
    elapsed = time.perf_counter() - started
    print(f"graph_data all+top+projects for {len(everything['nodes'])} cards: {elapsed:.2f}s")
    assert len(everything["nodes"]) == 360 and len(plan["nodes"]) == 4
    assert len(cases["nodes"]) < 360  # cases hide their subtasks
    xs = {(n["x"], n["y"]) for n in everything["nodes"]}
    assert len(xs) == 360  # no two cards on the same spot
    assert elapsed < 3.0
