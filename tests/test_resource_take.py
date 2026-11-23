"""Resources opened, copied, downloaded and zipped from a project or a task (D-096)."""

import io
import zipfile

from app.core.schema.planning import ProjectCreate
from app.core.schema.resources import LinkCreate, ResourceCreate
from app.features.projects import projects_core
from app.features.resources import resources_core


def test_take_them_away(app, signed_in):
    with app.app_context():
        project = projects_core.create(ProjectCreate(name="Loo"))
        link = LinkCreate(target_type="project", target_id=project.id)
        made = [
            resources_core.create(
                ResourceCreate(kind="note", title="How to deploy", body="# Deploy\nRun it."), link
            ),
            resources_core.create(
                ResourceCreate(kind="snippet", title="Start", body="print(1)", language="python"), link
            ),
            resources_core.create(
                ResourceCreate(kind="url", title="Docs", url="https://loo.example/docs"), link
            ),
            resources_core.create(ResourceCreate(kind="note", title="How to deploy", body="again"), link),
        ]
        ids = [str(r.id) for r in made]
    page = signed_in.get("/projects/loo?tab=about").data.decode()
    assert "Open here" in page and "data-copy-source" in page and "Download the chosen as a zip" in page
    text = signed_in.get(f"/resources/{ids[1]}/text")
    assert text.data == b"print(1)" and "Start.py" in text.headers["Content-Disposition"]
    assert signed_in.get(f"/resources/{ids[2]}/text").data.startswith(b"[InternetShortcut]")
    answer = signed_in.post("/resources/zip", data={"resource_ids": ids})
    names = sorted(zipfile.ZipFile(io.BytesIO(answer.data)).namelist())
    assert names == ["Docs.url", "How-to-deploy-2.md", "How-to-deploy.md", "Start.py"]
    assert b"Choose the resources" in signed_in.post("/resources/zip", follow_redirects=True).data
