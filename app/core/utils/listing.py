"""Server-side lists (PROJECT_BRIEF.md §14.3): search, filters, sort and pagination always run
in the database on the full dataset, and the whole state lives in the URL.

A feature declares a `ListSpec` once (which columns can be searched, filtered, sorted)
and calls `run_list(spec, base_query, request.args)`. Anything not declared is ignored,
so the URL can never sort or filter on an arbitrary column.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

from sqlalchemy import ColumnElement, Select, func, or_, select
from sqlalchemy.orm import InstrumentedAttribute

from app.core.extensions import db
from app.core.utils.settings import get_setting

Sortable = InstrumentedAttribute | ColumnElement

MAX_SEARCH_LENGTH = 200


@dataclass(frozen=True)
class FilterSpec:
    """A filter on `column` (value equality), or on named `conditions` (value -> SQL clause).

    Several values chosen for one filter are OR-ed; different filters are AND-ed.
    """

    name: str
    label: str
    column: InstrumentedAttribute | None
    choices: tuple[tuple[str, str], ...]  # (value, label)
    conditions: Mapping[str, ColumnElement] | None = None

    def clause(self, values: list[str]) -> ColumnElement:
        if self.conditions is not None:
            return or_(*(self.conditions[value] for value in values))
        return self.column.in_(values)


@dataclass(frozen=True)
class ListSpec:
    sortable: Mapping[str, Sortable]
    default_sort: str
    default_direction: str = "desc"
    searchable: tuple[InstrumentedAttribute, ...] = ()
    filters: tuple[FilterSpec, ...] = ()
    views: tuple[str, ...] = ("table", "cards")
    tiebreak: Sortable | None = None  # unique column: stable pages when sort values tie


@dataclass
class ListPage:
    items: list[Any]
    total: int
    page: int
    per_page: int
    sort: str
    direction: str
    search: str
    view: str
    active_filters: dict[str, list[str]]
    per_page_choices: list[int]
    spec: ListSpec
    extra: dict[str, str] = field(default_factory=dict)

    @property
    def pages(self) -> int:
        return max(1, math.ceil(self.total / self.per_page))

    @property
    def first_index(self) -> int:
        return 0 if self.total == 0 else (self.page - 1) * self.per_page + 1

    @property
    def last_index(self) -> int:
        return min(self.total, self.page * self.per_page)

    def state(self, **changes: Any) -> dict[str, Any]:
        """The current URL state with some values changed (None removes a value)."""
        params: dict[str, Any] = {
            "q": self.search or None,
            "sort": self.sort if self.sort != self.spec.default_sort else None,
            "dir": self.direction if self.direction != self.spec.default_direction else None,
            "page": self.page if self.page > 1 else None,
            "per_page": self.per_page if self.per_page != self.per_page_choices[0] else None,
            "view": self.view if self.view != self.spec.views[0] else None,
            **{name: values for name, values in self.active_filters.items() if values},
            **self.extra,
        }
        if any(key in changes for key in ("q", "sort", "dir", "per_page", *self.active_filters)):
            params["page"] = None  # a new query starts from the first page
        params.update(changes)
        return {k: v for k, v in params.items() if v not in (None, "", [])}

    def url(self, **changes: Any) -> str:
        return "?" + urlencode(self.state(**changes), doseq=True)

    def _without_search(self) -> dict[str, None]:
        return {"q": None, **dict.fromkeys(self.active_filters)}

    def clear_url(self) -> str:
        """Same sort, view and page size, no search and no filter."""
        return self.url(**self._without_search())

    def hidden_fields(self, *drop: str, search: bool = False) -> list[tuple[str, str]]:
        """The state as (name, value) pairs for a GET form's hidden inputs.

        `drop` names the fields the form itself shows; `search=True` also leaves out the
        search and filters (the toolbar form carries them as visible fields).
        """
        changes: dict[str, Any] = dict.fromkeys(drop)
        if search:
            changes |= self._without_search()
        pairs: list[tuple[str, str]] = []
        for name, value in self.state(**changes).items():
            values = value if isinstance(value, list) else [value]
            pairs.extend((name, str(item)) for item in values)
        return pairs

    def sort_url(self, column: str) -> str:
        direction = "asc" if self.sort == column and self.direction == "desc" else "desc"
        return self.url(sort=column, dir=direction)

    def aria_sort(self, column: str) -> str:
        if self.sort != column:
            return "none"
        return "ascending" if self.direction == "asc" else "descending"

    @property
    def has_filters(self) -> bool:
        return bool(self.search) or any(self.active_filters.values())


def _positive_int(raw: str | None, default: int) -> int:
    try:
        value = int(raw or default)
    except ValueError:
        return default
    return value if value > 0 else default


def escape_like(text: str) -> str:
    """The search is a plain substring: `%` and `_` typed by the owner are not wildcards."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def run_list(spec: ListSpec, query: Select, args: Mapping[str, Any]) -> ListPage:
    per_page_choices: list[int] = list(get_setting("lists.per_page"))
    per_page = _positive_int(args.get("per_page"), per_page_choices[0])
    if per_page not in per_page_choices:
        per_page = per_page_choices[0]

    sort = args.get("sort") if args.get("sort") in spec.sortable else spec.default_sort
    direction = args.get("dir") if args.get("dir") in ("asc", "desc") else spec.default_direction
    view = args.get("view") if args.get("view") in spec.views else spec.views[0]
    search = (args.get("q") or "").strip()[:MAX_SEARCH_LENGTH]

    if search and spec.searchable:
        pattern = f"%{escape_like(search)}%"
        query = query.where(or_(*(column.ilike(pattern, escape="\\") for column in spec.searchable)))

    active: dict[str, list[str]] = {}
    getlist = getattr(args, "getlist", None)
    for flt in spec.filters:
        allowed = {value for value, _ in flt.choices}
        raw = getlist(flt.name) if getlist else ([args[flt.name]] if flt.name in args else [])
        values = [value for value in raw if value in allowed]
        active[flt.name] = values
        if values:
            query = query.where(flt.clause(values))

    total = db.session.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    pages = max(1, math.ceil(total / per_page))
    page = min(_positive_int(args.get("page"), 1), pages)

    column = spec.sortable[sort]
    ordered = query.order_by(column.asc() if direction == "asc" else column.desc())
    items = list(db.session.scalars(ordered.limit(per_page).offset((page - 1) * per_page)))
    return ListPage(
        items, total, page, per_page, sort, direction, search, view, active, per_page_choices, spec
    )
