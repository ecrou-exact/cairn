import json
import time

import pytest

from app.core.db_class.job import Event
from app.core.extensions import db
from app.core.utils import events
from app.core.utils.events import EventCursor, matches, parse_topics, publish


def _publish(n, event_type="job.changed"):
    for i in range(n):
        publish(event_type, {"n": i})
    db.session.commit()


def test_publish_validates_type(ctx):
    with pytest.raises(ValueError):
        publish("NoDots")


def test_events_rolled_back_are_never_seen(ctx):
    publish("job.changed", {"x": 1})
    db.session.rollback()
    assert EventCursor(0).poll() == []


def test_topics():
    assert parse_topics("job, setting.changed") == ("job", "setting.changed")
    assert parse_topics("") == ()
    with pytest.raises(ValueError):
        parse_topics("job;drop")
    assert matches("job.log", ("job",)) and not matches("jobs.log", ("job",))
    assert matches("anything.here", ())


def test_cursor_reads_in_order_and_filters(ctx):
    _publish(3)
    _publish(1, "setting.changed")
    cursor = EventCursor(0, ("job",))
    assert [e.payload["n"] for e in cursor.poll()] == [0, 1, 2]
    assert cursor.last_id == 4
    assert cursor.poll() == []


def test_cursor_waits_on_a_gap_then_gives_up(ctx, monkeypatch):
    _publish(3)
    first, second, third = db.session.query(Event).order_by(Event.id).all()
    db.session.delete(second)  # an id whose transaction has not committed yet
    db.session.commit()
    cursor = EventCursor(0)
    assert [e.id for e in cursor.poll()] == [first.id, third.id]
    assert cursor.last_id == first.id  # resume below the gap
    assert cursor.poll() == []  # third is not delivered twice
    clock = time.monotonic() + events.GAP_WAIT_SECONDS + 1
    monkeypatch.setattr(events.time, "monotonic", lambda: clock)
    cursor.poll()
    assert cursor.last_id == third.id


def test_event_ids_are_not_reused_after_a_prune(ctx):
    _publish(2)
    db.session.query(Event).delete()
    db.session.commit()
    _publish(1)
    assert db.session.query(Event).one().id == 3


def test_sse_endpoint(app, signed_in):
    with app.app_context():
        _publish(2)
        _publish(1, "setting.changed")
    response = signed_in.get("/events?topics=job&after=0")
    assert response.mimetype == "text/event-stream"
    body = response.get_data(as_text=True)
    assert body.startswith("retry: 2000\nid: 0\n")
    data = [json.loads(line[6:]) for line in body.splitlines() if line.startswith("data: ")]
    assert [d["type"] for d in data] == ["job.changed", "job.changed"]
    resumed = signed_in.get("/events?topics=job", headers={"Last-Event-ID": "1"}).get_data(as_text=True)
    assert resumed.count("data: ") == 1
    assert signed_in.get("/events?topics=bad;topic").status_code == 400


def test_sse_needs_the_owner(client, owner):
    assert client.get("/events").status_code == 302
