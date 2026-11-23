"""A git worktree per Claude (D-077)."""

import shutil
import subprocess
from pathlib import Path

import pytest

from app.core.extensions import db
from app.core.schema.claude import SessionStart
from app.core.schema.planning import ProjectCreate, TaskCreate
from app.core.utils.settings import set_setting
from app.features.claude import terminal_core, worktrees_core
from app.features.projects import projects_core
from app.features.tasks import tasks_core
from tests.test_claude import fake_claude  # noqa: F401 (a fixture)

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="needs git")


def _git(folder, *args):
    who = ["-c", "user.name=t", "-c", "user.email=t@example.org", "-c", "commit.gpgsign=false"]
    done = subprocess.run(  # noqa: S603
        ["git", *who, "-C", str(folder), *args],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout.strip()


@pytest.fixture
def repo(ctx, tmp_path):
    folder = tmp_path / "site"
    folder.mkdir()
    _git(folder, "init", "-q", "-b", "main")
    (folder / "a.txt").write_text("a")
    _git(folder, "add", "-A")
    _git(folder, "commit", "-qm", "first")
    project = projects_core.create(ProjectCreate(name="Site", local_path=str(folder)))
    return project, folder


def _task(project, title="Fix the login; rm -rf"):
    return tasks_core.create(TaskCreate(title=title, project_id=project.id, type="bug"))


def test_a_task_gets_its_own_folder_and_branch(repo, fake_claude):  # noqa: F811
    project, folder = repo
    first, second = _task(project), _task(project, "Other")
    one = terminal_core.start(SessionStart(task_id=first.id, with_brief=True))
    two = terminal_core.start(SessionStart(task_id=second.id, with_brief=True))
    assert len({one.cwd, two.cwd, str(folder)}) == 3 and one.project_id == project.id
    assert _git(one.cwd, "branch", "--show-current") == "bug/fix-the-login-rm-rf"
    assert _git(folder, "branch", "--show-current") == "main"  # the main folder is not touched
    assert terminal_core.start(SessionStart(task_id=first.id)).cwd == one.cwd  # found again
    assert "bug/fix-the-login-rm-rf" in worktrees_core.rules(one.cwd) and not worktrees_core.rules(
        str(folder)
    )
    assert terminal_core.start(SessionStart(project_id=project.id)).cwd == str(folder)
    asked = terminal_core.start(SessionStart(project_id=project.id, worktree=True))
    assert asked.cwd != str(folder) and _git(asked.cwd, "branch", "--show-current").startswith("claude/")
    third = _task(project, "Third")
    assert terminal_core.start(SessionStart(task_id=third.id, worktree=False)).cwd == str(folder)


def test_what_is_not_git_is_used_as_it_is(ctx, tmp_path, fake_claude):  # noqa: F811
    plain = projects_core.create(ProjectCreate(name="Plain", local_path=str(tmp_path)))
    task = _task(plain)
    assert terminal_core.start(SessionStart(task_id=task.id)).cwd == str(tmp_path)
    with pytest.raises(terminal_core.TerminalError, match="not a git repository"):
        terminal_core.start(SessionStart(task_id=task.id, worktree=True))
    with pytest.raises(ValueError):
        SessionStart(folder=str(tmp_path), worktree=True)


def test_the_setting_decides(repo, fake_claude):  # noqa: F811
    project, folder = repo
    set_setting("claude.worktrees", False)
    assert terminal_core.start(SessionStart(task_id=_task(project).id)).cwd == str(folder)


def test_removing_keeps_the_work(repo):
    project, folder = repo
    row = worktrees_core.open_for(project, _task(project), folder)
    path = Path(row.path)
    (path / "new.txt").write_text("work")
    told = worktrees_core.describe(row)
    assert (told["changes"], told["commits"], told["here"]) == (1, 0, True)
    with pytest.raises(worktrees_core.WorktreeError, match="not committed"):
        worktrees_core.remove(row.id)
    assert (path / "new.txt").is_file()
    _git(path, "add", "-A")
    _git(path, "commit", "-qm", "work")
    assert worktrees_core.describe(row)["commits"] == 1
    worktrees_core.remove(row.id)
    assert not path.exists() and worktrees_core.live(project.id) == []
    assert "work" in _git(folder, "log", "--format=%s", row.branch)  # its branch stays
    again = worktrees_core.open_for(project, _task(project), folder)
    assert again.branch == f"{row.branch}-2"  # an existing branch is never taken over


def test_not_while_a_claude_is_in_it_nor_elsewhere(repo, fake_claude, tmp_path):  # noqa: F811
    project, folder = repo
    session = terminal_core.start(SessionStart(task_id=_task(project).id))
    row = worktrees_core.for_path(session.cwd)
    with pytest.raises(worktrees_core.WorktreeError, match="Claude is open"):
        worktrees_core.remove(row.id)
    terminal_core.close_all()
    db.session.expire_all()
    kept = row.path
    row.path = str(folder)  # a row that names a folder Cairn did not make
    db.session.commit()
    with pytest.raises(worktrees_core.WorktreeError, match="not one Cairn made"):
        worktrees_core.remove(row.id)
    assert folder.is_dir() and Path(kept).is_dir()


def test_tab_and_api(signed_in, repo):
    project, folder = repo
    row = worktrees_core.open_for(project, _task(project), folder)
    page = signed_in.get(f"/projects/{project.slug}?tab=claude").data.decode()
    assert row.branch in page and "Remove the folder" in page
    listed = signed_in.get(f"/api/claude/worktrees?project={project.id}").json["worktrees"]
    assert [w["branch"] for w in listed] == [row.branch]
    assert signed_in.get("/api/claude/worktrees").status_code == 422
    assert signed_in.get("/api/claude/targets").json["worktrees"] is True
    assert signed_in.delete(f"/api/claude/worktrees/{row.id}").status_code == 200
    assert signed_in.delete(f"/api/claude/worktrees/{row.id}").status_code == 409
