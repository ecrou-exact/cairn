from datetime import date, timedelta

from app.core.schema.planning import TaskCreate
from app.core.utils.history import batch
from app.features.home import home_core
from app.features.tasks import tasks_core


def test_today_tells_what_to_do_and_why(ctx):
    soon = tasks_core.create(
        TaskCreate(title="Ship it", priority="critical", due_on=date.today() + timedelta(days=2))
    )
    tasks_core.create(TaskCreate(title="Later", priority="low"))
    with batch():
        tasks_core.set_status(soon.id, "in_progress")
    data = home_core.today()
    assert data["focus"].title == "Ship it"
    assert data["focus_reasons"] and data["focus_reasons"][0].startswith("Priority")
    assert [t.title for t in data["next_actions"]] == ["Later"]
    days = data["week"]["days"]
    assert len(days) == 7 and days[0]["today"] and [t.title for t in days[2]["tasks"]] == ["Ship it"]
    told = data["activity"][0]
    assert (told["who"], told["verb"], told["name"], told["after"]) == (
        "You",
        "moved",
        "Ship it",
        "to In progress",
    )


def test_today_page_renders(app, signed_in):
    page = signed_in.get("/")
    assert page.status_code == 200 and b"Next up" in page.data and b"This week" in page.data
    assert b"style=" not in page.data
