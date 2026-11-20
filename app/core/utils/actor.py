"""Who is acting right now: the owner, a Claude run or a module.

Every write records its actor (`created_by`, activity log). Web requests act as
`user`; background work wraps itself in `acting_as("claude:<run-id>")` or
`acting_as("module:<id>")`.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_ACTOR_PATTERN = re.compile(r"^(user|system|claude:[\w-]{1,64}|module:[\w.-]{1,64})$")
_current: ContextVar[str] = ContextVar("cairn_actor", default="user")


def current_actor() -> str:
    return _current.get()


@contextmanager
def acting_as(actor: str) -> Iterator[None]:
    if not _ACTOR_PATTERN.match(actor):
        raise ValueError(f"Invalid actor '{actor}'.")
    token = _current.set(actor)
    try:
        yield
    finally:
        _current.reset(token)
