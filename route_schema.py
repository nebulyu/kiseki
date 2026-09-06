"""Validated local goal and route configuration, without analysis or scoring."""

import re
from datetime import date
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


ConfigText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
ContentVersion = Annotated[int, Field(strict=True, ge=1)]
FocusDimension = Literal[
    "technical_growth",
    "relationship_capital",
    "information_gain",
    "social_engagement",
    "wellbeing",
    "autonomy",
]


class GoalDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: ConfigText
    version: ContentVersion
    name: ConfigText
    status: Literal["active", "paused", "completed"]
    description: ConfigText
    motivation: ConfigText
    target_date: date | None
    success_criteria: list[ConfigText]
    constraints: list[ConfigText]

    @field_validator("target_date", mode="before")
    @classmethod
    def parse_target_date(cls, value: object) -> date | None:
        if value is None:
            return None
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            raise ValueError("target_date must be null or a quoted YYYY-MM-DD string")
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise ValueError("target_date must be a valid calendar date (YYYY-MM-DD)") from error


class GoalsFile(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal["0.1.0"]
    goals: list[GoalDefinition]


class SpecificSignal(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: ConfigText
    label: ConfigText
    match_when: ConfigText
    daily_delta: int = Field(strict=True, ge=1, le=5)


class RouteCost(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: ConfigText
    label: ConfigText
    match_when: ConfigText
    daily_delta: int = Field(strict=True, ge=-5, le=-1)


class RouteCalculation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    formula_version: Literal["route-evidence-0.1.0"]
    method: Literal["sum_unique_signals_clamped"]
    daily_delta_range: list[Annotated[int, Field(strict=True)]] = Field(
        min_length=2, max_length=2
    )
    missing_value: None

    @field_validator("daily_delta_range")
    @classmethod
    def require_current_range(cls, value: list[int]) -> list[int]:
        if value != [-5, 5]:
            raise ValueError("daily_delta_range must be [-5, 5]")
        return value


class RouteDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal["0.2.0"]
    id: ConfigText
    version: ContentVersion
    goal_id: ConfigText
    name: ConfigText
    status: Literal["exploring", "active", "paused", "archived"]
    description: ConfigText
    key_hypotheses: list[ConfigText]
    focus_dimensions: list[FocusDimension]
    specific_signals: list[SpecificSignal]
    costs: list[RouteCost]
    calculation: RouteCalculation

    @model_validator(mode="after")
    def require_unique_signal_ids(self) -> "RouteDefinition":
        seen: dict[str, str] = {}
        for field_name in ("specific_signals", "costs"):
            for index, signal in enumerate(getattr(self, field_name)):
                location = f"{field_name}[{index}]"
                if signal.id in seen:
                    raise ValueError(
                        f"duplicate signal id {signal.id!r} in {location}; "
                        f"already defined in {seen[signal.id]}"
                    )
                seen[signal.id] = location
        return self


class RouteConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    goals: dict[str, GoalDefinition]
    routes: dict[str, RouteDefinition]
