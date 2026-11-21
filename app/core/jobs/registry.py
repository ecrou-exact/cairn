"""Job handler registry: `@register_handler("type", lane=..., title=...)`."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.core.jobs.context import JobContext

Handler = Callable[["JobContext", dict[str, Any]], dict[str, Any] | None]


@dataclass(frozen=True)
class HandlerSpec:
    type: str
    lane: str
    title: str
    func: Handler
    max_attempts: int
    timeout_seconds: int
    manual: bool  # the owner may start it from the Jobs page or the API


_handlers: dict[str, HandlerSpec] = {}


def register_handler(
    job_type: str,
    *,
    lane: str,
    title: str,
    max_attempts: int = 3,
    timeout_seconds: int = 600,
    manual: bool = False,
) -> Callable[[Handler], Handler]:
    def decorator(func: Handler) -> Handler:
        if job_type in _handlers:
            raise RuntimeError(f"Job type '{job_type}' is registered twice.")
        _handlers[job_type] = HandlerSpec(job_type, lane, title, func, max_attempts, timeout_seconds, manual)
        return func

    return decorator


def get_handler(job_type: str) -> HandlerSpec:
    try:
        return _handlers[job_type]
    except KeyError as exc:
        raise KeyError(f"No handler for job type '{job_type}'.") from exc


def handler_types() -> list[HandlerSpec]:
    return sorted(_handlers.values(), key=lambda spec: spec.type)


def manual_types() -> list[HandlerSpec]:
    return [spec for spec in handler_types() if spec.manual]
