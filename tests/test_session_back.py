"""The session page goes back where the owner came from; stopping is its own button (D-097)."""

import uuid

from app.core.db_class.claude import ClaudeSession
from app.core.extensions import db


def test_back_and_stop(app, signed_in):
    with app.app_context():
        row = ClaudeSession(cwd="/w", cli_session_id=uuid.uuid4(), kind="claude", status="ended")
        db.session.add(row)
        db.session.commit()
        url = f"/claude/sessions/{row.id}"
    page = signed_in.get(url, headers={"Referer": "http://localhost/tasks?view=table"}).data.decode()
    assert 'href="/tasks?view=table"' in page and ">Back<" in page
    alone = signed_in.get(url, headers={"Referer": "https://elsewhere.example/x"}).data.decode()
    assert 'href="/claude"' in alone and "elsewhere" not in alone
