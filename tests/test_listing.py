from werkzeug.datastructures import MultiDict

from app.core.extensions import db
from app.core.jobs import jobs_core
from app.core.utils.settings import set_setting


def _jobs(n, title="Job"):
    for i in range(n):
        jobs_core.enqueue("system.self_check", title=f"{title} {i:02d}")


def _run(**args):
    return jobs_core.list_jobs(MultiDict(args))


def test_pagination_runs_on_the_full_dataset(ctx):
    set_setting("lists.per_page", [5, 10])
    _jobs(12)
    first = _run()
    assert (first.total, first.pages, len(first.items), first.per_page) == (12, 3, 5, 5)
    last = _run(page="3")
    assert len(last.items) == 2 and (last.first_index, last.last_index) == (11, 12)
    assert _run(page="99").page == 3  # out of range: last page
    assert _run(page="-1").page == 1
    assert _run(per_page="7").per_page == 5  # only offered sizes


def test_search_is_literal_and_case_insensitive(ctx):
    _jobs(2, "Deploy")
    _jobs(1, "100%_done")
    assert _run(q="deploy").total == 2
    assert _run(q="%").total == 1 and _run(q="%_d").total == 1  # not wildcards: "_" is in every type too


def test_unknown_sort_and_filter_values_are_ignored(ctx):
    _jobs(2)
    page = _run(sort="password", dir="sideways", status="evil", view="poster")
    assert (page.sort, page.direction, page.view, page.total) == ("created", "desc", "table", 2)
    assert page.active_filters["status"] == []


def test_sort_and_filters(ctx):
    _jobs(3)
    job = jobs_core.enqueue("system.prune")
    jobs_core.cancel(job.id)
    assert _run(status="cancelled").total == 1
    multi = jobs_core.list_jobs(MultiDict([("status", "cancelled"), ("status", "queued")]))
    assert multi.total == 4
    titles = [j.title for j in _run(sort="type", dir="asc").items]
    assert titles[-1].startswith("Job")  # system.self_check after system.prune
    db.session.rollback()


def test_url_state(ctx):
    _jobs(1)
    page = _run(q="job", sort="type", dir="asc", status="queued")
    assert page.url() == "?q=job&sort=type&dir=asc&status=queued"
    assert page.url(sort="lane") == "?q=job&sort=lane&dir=asc&status=queued"
    assert page.clear_url() == "?sort=type&dir=asc"
    assert page.sort_url("type") == "?q=job&sort=type&dir=desc&status=queued"
    assert ("q", "job") not in page.hidden_fields("page", search=True)
    assert ("sort", "type") in page.hidden_fields("page", search=True)
