"""Settings and appearance as the API reads and changes them."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, JsonValue, TypeAdapter, model_validator

from app.core.schema.common import Strict


class SettingUpdate(Strict):
    value: JsonValue


class SettingOut(BaseModel):
    key: str
    label: str
    category: str
    description: str
    value: Any
    default: Any
    overridden: bool
    default_changed: bool

    @classmethod
    def from_state(cls, state) -> SettingOut:
        d = state.definition
        return cls(
            key=d.key,
            label=d.label,
            category=d.category,
            description=d.description,
            value=state.value,
            default=d.default,
            overridden=state.overridden,
            default_changed=state.default_changed,
        )


class ThemeUpdate(Strict):
    theme: str = Field(min_length=1, max_length=32, pattern=r"^[a-z][a-z0-9-]*$")


class Lanes(Strict):
    """Every lane must stay: a lane left out would never run its jobs."""

    agent: int = Field(ge=1, le=16)
    io: int = Field(ge=1, le=32)
    module: int = Field(ge=1, le=16)
    system: int = Field(ge=1, le=4)


KEY = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,29}$")]
LABEL = Annotated[str, Field(min_length=1, max_length=40)]


class WorkflowStatus(Strict):
    key: KEY
    label: LABEL
    kind: Literal["open", "active", "waiting", "done", "cancelled"]


class Workflow(Strict):
    default: KEY
    statuses: list[WorkflowStatus] = Field(min_length=2, max_length=20)
    transitions: dict[KEY, list[KEY]]

    @model_validator(mode="after")
    def _consistent(self) -> Workflow:
        keys = [s.key for s in self.statuses]
        if len(set(keys)) != len(keys):
            raise ValueError("status keys must be unique")
        kinds = {s.kind for s in self.statuses}
        if self.default not in keys or self.statuses[keys.index(self.default)].kind not in ("open", "active"):
            raise ValueError("the default status must be an open or active status of the list")
        if not {"done"} <= kinds or not kinds & {"open", "active"}:
            raise ValueError("needs at least one open or active status and one done status")
        for source, targets in self.transitions.items():
            unknown = {source, *targets} - set(keys)
            if unknown:
                raise ValueError(f"unknown status in transitions: {', '.join(sorted(unknown))}")
        return self


class TaskType(Strict):
    label: LABEL
    icon: Annotated[str, Field(pattern=r"^fa-[a-z0-9-]{1,40}$")]


WEIGHT = Annotated[float, Field(ge=0, le=100)]


class ScoreWeights(Strict):
    priority: WEIGHT
    importance: WEIGHT
    urgency: WEIGHT
    deadline: WEIGHT
    hard_deadline_bonus: WEIGHT
    unblocks: WEIGHT
    quick_win: WEIGHT
    age: WEIGHT
    deadline_horizon_days: int = Field(ge=1, le=365)


class Attention(Strict):
    due_soon_days: int = Field(ge=0, le=60)
    stale_active_days: int = Field(ge=1, le=90)


class Capacity(Strict):
    hours_per_day: float = Field(gt=0, le=24)
    work_days: list[Annotated[int, Field(ge=0, le=6)]] = Field(min_length=1, max_length=7)


class TemplateSubtask(Strict):
    title: Annotated[str, Field(min_length=1, max_length=200)]
    type: KEY


class TaskTemplate(Strict):
    label: LABEL
    type: KEY
    priority: Literal["critical", "high", "medium", "low"]
    tags: list[Annotated[str, Field(pattern=r"^[\w][\w.+-]{0,31}$")]] = Field(max_length=20)
    checklist: list[Annotated[str, Field(min_length=1, max_length=300)]] = Field(max_length=100)
    acceptance_md: Annotated[str, Field(max_length=20_000)]
    subtasks: list[TemplateSubtask] = Field(max_length=50)
    sequential: bool


class CustomField(Strict):
    label: LABEL
    type: Literal["text", "number", "date", "url", "select"]
    options: list[Annotated[str, Field(min_length=1, max_length=60)]] = Field(
        default_factory=list, max_length=50
    )
    hint: Annotated[str, Field(max_length=200)] = ""

    @model_validator(mode="after")
    def _options(self) -> CustomField:
        if self.type == "select" and not self.options:
            raise ValueError("a select field needs options")
        return self


THEME_NAMES = Literal["auto", "stone", "basalt", "moss", "ember"]

# One type per settings file (checked by tests/test_settings.py). An override must fit it.
SETTING_TYPES: dict[str, TypeAdapter] = {
    "jobs.lanes": TypeAdapter(Lanes),
    "tasks.workflow": TypeAdapter(Workflow),
    "tasks.types": TypeAdapter(Annotated[dict[KEY, TaskType], Field(min_length=1, max_length=40)]),
    "tasks.score_weights": TypeAdapter(ScoreWeights),
    "tasks.attention": TypeAdapter(Attention),
    "tasks.capacity": TypeAdapter(Capacity),
    "tasks.custom_fields": TypeAdapter(Annotated[dict[KEY, CustomField], Field(max_length=30)]),
    "tasks.templates": TypeAdapter(Annotated[dict[KEY, TaskTemplate], Field(max_length=50)]),
    "resources.max_upload_mb": TypeAdapter(Annotated[int, Field(strict=True, ge=1, le=50)]),
    "claude.main_autostart": TypeAdapter(Annotated[bool, Field(strict=True)]),
    "claude.cairn_writes_allowed": TypeAdapter(Annotated[bool, Field(strict=True)]),
    "claude.worktrees": TypeAdapter(Annotated[bool, Field(strict=True)]),
    "claude.max_open": TypeAdapter(Annotated[int, Field(strict=True, ge=1, le=50)]),
    "projects.transfer_folder": TypeAdapter(Annotated[str, Field(max_length=500)]),
    "projects.editor": TypeAdapter(Annotated[str, Field(pattern=r"^[A-Za-z0-9._-]{1,60}$")]),
    "resources.previews": TypeAdapter(Annotated[bool, Field(strict=True)]),
    "jobs.retention_days": TypeAdapter(Annotated[int, Field(strict=True, ge=1, le=3650)]),
    "lists.per_page": TypeAdapter(
        Annotated[list[Annotated[int, Field(strict=True, ge=5, le=500)]], Field(min_length=1, max_length=6)]
    ),
    "claude.context_windows": TypeAdapter(
        Annotated[
            dict[
                Annotated[str, Field(min_length=1, max_length=80)],
                Annotated[int, Field(strict=True, ge=8000, le=4_000_000)],
            ],
            Field(min_length=1, max_length=40),
        ]
    ),
    "claude.rules": TypeAdapter(
        Annotated[list[Annotated[str, Field(min_length=1, max_length=600)]], Field(max_length=40)]
    ),
    "recap.folders": TypeAdapter(
        Annotated[list[Annotated[str, Field(min_length=1, max_length=300)]], Field(max_length=20)]
    ),
    "recap.ignored": TypeAdapter(
        Annotated[list[Annotated[str, Field(min_length=1, max_length=100)]], Field(max_length=200)]
    ),
    "recap.day_start": TypeAdapter(Annotated[str, Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]),
    "recap.day_minutes": TypeAdapter(Annotated[int, Field(strict=True, ge=15, le=1440)]),
    "ui.themes": TypeAdapter(
        Annotated[dict[THEME_NAMES, Annotated[str, Field(min_length=1, max_length=60)]], Field(min_length=1)]
    ),
}
