from datetime import datetime, timezone

from schema import (
    AnalysisResult,
    AnalysisReview,
    EffectiveResult,
    ReviewState,
    ReviewStatus,
    ScoreField,
    ScoreValue,
    ScoreValues,
)


SCORE_FIELDS: tuple[ScoreField, ...] = (
    "overall_score",
    "technical_growth",
    "relationship_capital",
    "information_gain",
    "social_engagement",
    "wellbeing",
    "autonomy",
)


def extract_ai_scores(analysis: AnalysisResult) -> ScoreValues:
    return ScoreValues(
        overall_score=analysis.overall_score,
        technical_growth=analysis.dimensions.technical_growth.score,
        relationship_capital=analysis.dimensions.relationship_capital.score,
        information_gain=analysis.dimensions.information_gain.score,
        social_engagement=analysis.dimensions.social_engagement.score,
        wellbeing=analysis.dimensions.wellbeing.score,
        autonomy=analysis.dimensions.autonomy.score,
    )


def derive_review_state(
    review: AnalysisReview | None,
    *,
    analysis_revision: int,
    analysis_model: str | None,
    prompt_version: str | None,
) -> ReviewState:
    if review is None:
        return "unreviewed"
    if (
        review.analysis_revision != analysis_revision
        or review.analysis_model != analysis_model
        or review.prompt_version != prompt_version
    ):
        return "stale"
    return review.status


def calculate_effective_scores(
    analysis: AnalysisResult,
    review: AnalysisReview | None,
    *,
    analysis_revision: int,
    analysis_model: str | None,
    prompt_version: str | None,
) -> EffectiveResult:
    state = derive_review_state(
        review,
        analysis_revision=analysis_revision,
        analysis_model=analysis_model,
        prompt_version=prompt_version,
    )
    ai_scores = extract_ai_scores(analysis)

    if state == "rejected":
        return EffectiveResult(state=state, scores=None)
    if state != "adjusted":
        return EffectiveResult(state=state, scores=ai_scores)

    scores = ai_scores.model_dump()
    for field, value in review.overrides.items():
        scores[field] = value
    return EffectiveResult(state=state, scores=ScoreValues.model_validate(scores))


def create_review(
    *,
    status: ReviewStatus,
    overrides: dict[ScoreField, ScoreValue],
    reason: str,
    analysis_revision: int,
    analysis_model: str | None,
    prompt_version: str | None,
    reviewed_at: datetime | None = None,
) -> AnalysisReview:
    return AnalysisReview(
        status=status,
        overrides=overrides,
        reason=reason,
        analysis_revision=analysis_revision,
        analysis_model=analysis_model,
        prompt_version=prompt_version,
        reviewed_at=reviewed_at or datetime.now(timezone.utc),
    )
