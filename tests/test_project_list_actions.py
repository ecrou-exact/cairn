"""Projects marked in place and together; filters (D-089)."""

from app.core.schema.planning import ProjectCreate
from app.features.projects import projects_core


def _two(app):
    with app.app_context():
        ids = [
            str(projects_core.create(ProjectCreate(name=n, github_repo=r)).id)
            for n, r in (("A", "acme/a"), ("B", None))
        ]
    return ids


def test_bulk_and_filters(app, signed_in):
    a, b = _two(app)
    page = signed_in.get("/projects").data.decode()
    assert "data-project-bulk" in page and 'data-project-marks="' + a in page
    done = signed_in.post(
        "/projects/bulk", data={"action": "star", "project_ids": [a, b]}, follow_redirects=True
    )
    assert b"2 projects changed" in done.data
    assert signed_in.patch(f"/api/projects/{b}", json={"pinned": True}).status_code == 200
    assert "/projects/b" in signed_in.get("/projects?mark=pinned&view=table").data.decode()
    assert '/projects/a"' not in signed_in.get("/projects?mark=pinned&view=table").data.decode()
    assert "/projects/a" in signed_in.get("/projects?owner=acme&view=table").data.decode()
    assert '/projects/a"' not in signed_in.get("/projects?owner=none&view=table").data.decode()
    signed_in.post("/projects/bulk", data={"action": "hide", "project_ids": [a]})
    assert '/projects/a"' not in signed_in.get("/projects?view=table").data.decode()
    table = signed_in.get("/projects?hidden=1&view=table").data.decode()
    assert "cn-row-actions" in table and "Show" in table
    assert (
        b"Choose projects"
        in signed_in.post("/projects/bulk", data={"action": "star"}, follow_redirects=True).data
    )
    assert signed_in.post("/projects/bulk", data={"action": "star", "project_ids": ["x"]}).status_code == 400
