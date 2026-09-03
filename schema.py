from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


WarningText = Annotated[str, StringConstraints(max_length=200)]
ScoreValue = Annotated[int, Field(ge=0, le=100)] | None
EvidenceDimension = Literal[
    "overall_experience",
    "technical_growth",
    "relationship_capital",
    "information_gain",
    "social_engagement",
    "wellbeing",
    "autonomy",
]
ScoreField = Literal[
    "overall_score",
    "technical_growth",
    "relationship_capital",
    "information_gain",
    "social_engagement",
    "wellbeing",
    "autonomy",
]
ReviewStatus = Literal["accepted", "adjusted", "rejected"]
ReviewState = Literal[
    "unreviewed",
    "accepted",
    "adjusted",
    "rejected",
    "stale",
]


class DimensionScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int | None = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[str] = Field(json_schema_extra={"uniqueItems": True})
    rationale: str = Field(max_length=300)

    @field_validator("evidence_ids")
    @classmethod
    def evidence_ids_must_be_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("evidence_ids must contain unique values")
        return value


class Dimensions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    technical_growth: DimensionScore
    relationship_capital: DimensionScore
    information_gain: DimensionScore
    social_engagement: DimensionScore
    wellbeing: DimensionScore
    autonomy: DimensionScore


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^e[0-9]+$")
    source_excerpt: str = Field(min_length=1, max_length=120)
    dimension: EvidenceDimension
    impact: float = Field(ge=-1, le=1)
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(min_length=1, max_length=300)


class AnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["0.1.0"]
    entry_date: date
    overall_score: int | None = Field(ge=0, le=100)
    dimensions: Dimensions
    summary: str = Field(min_length=1, max_length=500)
    evidence: list[EvidenceItem]
    confidence: float = Field(ge=0, le=1)
    warnings: list[WarningText]


class ScoreValues(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overall_score: ScoreValue
    technical_growth: ScoreValue
    relationship_capital: ScoreValue
    information_gain: ScoreValue
    social_engagement: ScoreValue
    wellbeing: ScoreValue
    autonomy: ScoreValue


class AnalysisReview(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal["0.1.0"] = "0.1.0"
    status: ReviewStatus
    overrides: dict[ScoreField, ScoreValue] = Field(default_factory=dict)
    reason: str = Field(default="", max_length=1000)
    analysis_revision: int = Field(ge=0)
    analysis_model: str | None
    prompt_version: str | None
    reviewed_at: datetime

    @model_validator(mode="after")
    def validate_status_fields(self) -> "AnalysisReview":
        if self.status == "adjusted" and not self.overrides:
            raise ValueError("adjusted review requires at least one override")
        if self.status != "adjusted" and self.overrides:
            raise ValueError(f"{self.status} review cannot contain overrides")
        if self.status == "rejected" and not self.reason.strip():
            raise ValueError("rejected review requires a reason")
        return self


class EffectiveResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: ReviewState
    scores: ScoreValues | None
