"""Realtime events: `publish()` in core code, read by `GET /events` (SSE).

Events are rows in the `event` table, written in the same transaction as the change
they describe, so a view never hears about a change that was rolled back. Any process
(web or worker) can publish; the stream polls the table, which works on SQLite and
PostgreSQL alike (docs/DECISIONS.md D-020).
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Iterable, Iterator
from datetime import timedelta
from typing import Any

from sqlalchemy import delete, func, select

from app.core.db_class.base import utcnow
from app.core.db_class.job import Event
from app.core.extensions import db

_TYPE = re.compile(r"^[a-z][a-z_]*(\.[a-z_]+)+$")
_TOPIC = re.compile(r"^[a-z][a-z_]*(\.[a-z_]+)*$")
GAP_WAIT_SECONDS = 5.0
BATCH = 200
KEEP_ALIVE_SECONDS = 15


def publish(event_type: str, payload: dict[str, Any] | None = None) -> None:
    """Queue an event in the current session; it is delivered once the session commits."""
    if not _TYPE.match(event_type):
        raise ValueError(f"Invalid event type '{event_type}'.")
    db.session.add(Event(type=event_type, payload=payload or {}))


def parse_topics(raw: str | None) -> tuple[str, ...]:
    """`job,setting.changed` → topics a stream is limited to; empty means every event."""
    topics = tuple(t for t in (part.strip() for part in (raw or "").split(",")) if t)
    for topic in topics:
        if not _TOPIC.match(topic) or len(topic) > 80:
            raise ValueError(f"Invalid topic '{topic}'.")
    return topics


def matches(event_type: str, topics: Iterable[str]) -> bool:
    topics = tuple(topics)
    return not topics or any(event_type == t or event_type.startswith(t + ".") for t in topics)


def latest_event_id() -> int:
    return db.session.scalar(select(func.max(Event.id))) or 0


class EventCursor:
    """Reads new events in id order without losing any.

    Ids come from a sequence, so on PostgreSQL a transaction can commit id 41 after 42
    was already read. When ids jump, the cursor keeps reading from below the gap for
    `GAP_WAIT_SECONDS`, then gives up on it (an id used by a rolled-back transaction
    never appears). On SQLite writes are serialised and gaps close at once.
    """

    def __init__(self, after: int, topics: tuple[str, ...] = ()) -> None:
        self.floor = after  # every id <= floor was delivered or abandoned
        self.topics = topics
        self._seen: set[int] = set()
        self._gaps: dict[int, float] = {}  # missing id -> first time it was noticed

    def poll(self) -> list[Event]:
        rows = list(
            db.session.scalars(select(Event).where(Event.id > self.floor).order_by(Event.id).limit(BATCH))
        )
        db.session.rollback()  # end the read transaction: the next poll sees new commits
        now = time.monotonic()
        fresh = [row for row in rows if row.id not in self._seen]
        expected = self.floor + 1
        for row in rows:
            for missing in range(expected, row.id):
                if missing not in self._seen:
                    self._gaps.setdefault(missing, now)
            expected = max(expected, row.id + 1)
            self._seen.add(row.id)
            self._gaps.pop(row.id, None)
        for missing, since in list(self._gaps.items()):
            if now - since >= GAP_WAIT_SECONDS:
                del self._gaps[missing]
                self._seen.add(missing)
        while self.floor + 1 in self._seen:
            self.floor += 1
            self._seen.discard(self.floor)
        return [row for row in fresh if matches(row.type, self.topics)]

    @property
    def last_id(self) -> int:
        """What a client should send back as Last-Event-ID to resume here."""
        return self.floor


def sse_stream(
    after: int | None, topics: tuple[str, ...], *, lifetime: float, poll_every: float = 1.0
) -> Iterator[str]:
    """Server-Sent Events text for one connection.

    Each message is `id: <resume point>` + `data: {"id", "type", "payload"}`. The stream
    ends after `lifetime` seconds and the browser reconnects by itself with Last-Event-ID,
    so a long-lived connection never pins a server thread for good. Clients drop messages
    whose `data.id` they already saw (a resume point below an open gap replays a few).
    """
    cursor = EventCursor(latest_event_id() if after is None else after, topics)
    db.session.rollback()
    yield f"retry: 2000\nid: {cursor.last_id}\n: connected\n\n"
    started = last_sent = time.monotonic()
    while True:
        for event in cursor.poll():
            data = json.dumps({"id": event.id, "type": event.type, "payload": event.payload})
            yield f"id: {cursor.last_id}\ndata: {data}\n\n"
            last_sent = time.monotonic()
        now = time.monotonic()
        if now - started >= lifetime:
            return
        if now - last_sent >= KEEP_ALIVE_SECONDS:
            yield ": keep-alive\n\n"
            last_sent = now
        time.sleep(poll_every)


def prune_events(older_than: timedelta = timedelta(days=1)) -> int:
    result = db.session.execute(delete(Event).where(Event.created_at < utcnow() - older_than))
    return result.rowcount or 0
