import argparse
import json
import time
from datetime import date
from pathlib import Path

from database import (
    fetch_recent_records,
    fetch_record,
    insert_record,
    store_analysis,
    store_analysis_error,
    store_review,
)
from model import PROMPT_VERSION, analyze_entry, get_model_name
from review import (
    SCORE_FIELDS,
    calculate_effective_scores,
    create_review,
    derive_review_state,
    extract_ai_scores,
)
from schema import AnalysisResult, AnalysisReview, ScoreField, ScoreValue


LIST_LIMIT = 20
SUPPORTED_ENTRY_SUFFIXES = {".md", ".txt"}
SCORE_LABELS = {
    "overall_score": "Overall score",
    "technical_growth": "Technical growth",
    "relationship_capital": "Relationship capital",
    "information_gain": "Information gain",
    "social_engagement": "Social engagement",
    "wellbeing": "Wellbeing",
    "autonomy": "Autonomy",
}


def parse_entry_date(value: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as error:
        raise SystemExit("Date must use YYYY-MM-DD format.") from error


def read_entry_file(file_path: Path) -> str:
    path = file_path.expanduser()
    if path.suffix.lower() not in SUPPORTED_ENTRY_SUFFIXES:
        raise SystemExit("File must use .md or .txt format.")
    if not path.is_file():
        raise SystemExit(f"File not found: {path}")

    try:
        raw_text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as error:
        raise SystemExit(f"File must be UTF-8 encoded: {path}") from error
    except OSError as error:
        raise SystemExit(f"Could not read file: {path}: {error}") from error

    if not raw_text.strip():
        raise SystemExit(f"File is empty: {path}")
    return raw_text.strip()


def add_record(file_path: Path | None = None, date_value: str | None = None) -> None:
    today = date.today().isoformat()
    if date_value is None and file_path is None:
        date_value = input(f"Date [{today}]: ").strip() or today
    entry_date = parse_entry_date(date_value or today)

    if file_path is not None:
        raw_text = read_entry_file(file_path)
        print(f"Loaded {len(raw_text)} characters from {file_path}.")
    else:
        raw_text = input("Text: ")
    if not raw_text.strip():
        raise SystemExit("Text cannot be empty.")

    record_id = insert_record(entry_date, raw_text)

    print(f"Saved record {record_id}.")
    run_analysis(record_id, entry_date, raw_text)


def run_analysis(
    record_id: int,
    entry_date: str,
    raw_text: str,
) -> tuple[AnalysisResult, int, float]:
    started_at = time.perf_counter()

    try:
        configured_model = get_model_name()
        print(
            f"Analyzing record {record_id} with {configured_model}...",
            flush=True,
        )
        model_name, analysis = analyze_entry(entry_date, raw_text)
    except Exception as error:
        elapsed = time.perf_counter() - started_at
        store_analysis_error(record_id, str(error))
        raise SystemExit(
            f"Analysis failed for record {record_id} after {elapsed:.1f} seconds: "
            f"{error}"
        ) from error

    elapsed = time.perf_counter() - started_at
    revision = store_analysis(
        record_id,
        model=model_name,
        analysis_json=analysis.model_dump_json(),
        prompt_version=PROMPT_VERSION,
    )

    print(f"Analysis completed in {elapsed:.1f} seconds.")
    print(f"Analysis revision: {revision}")
    score = "null" if analysis.overall_score is None else analysis.overall_score
    print(f"Overall score: {score}")
    print(f"Summary: {analysis.summary}")
    print(f"Confidence: {analysis.confidence:.2f}")
    return analysis, revision, elapsed


def confirm_reanalysis() -> bool:
    while True:
        answer = input("Analyze again? [y/N]: ").strip().lower()
        if answer in {"", "n", "no"}:
            return False
        if answer in {"y", "yes"}:
            return True
        print("Enter y or n.")


def analyze_record(record_id: int) -> None:
    record = fetch_record(record_id)
    if record is None:
        raise SystemExit(f"Record {record_id} not found.")

    if record["analysis_json"]:
        print(f"Record {record_id} already has an AI analysis.")
        print(f"Current model: {record['model'] or '-'}")
        print(f"Current revision: {record['analysis_revision']}")
        if record["error_message"]:
            print(f"Latest reanalysis failed: {record['error_message']}")
        if not confirm_reanalysis():
            print("Analysis unchanged.")
            return

    run_analysis(record_id, record["entry_date"], record["raw_text"])


def parse_review(review_json: str | None) -> AnalysisReview | None:
    if review_json is None:
        return None
    return AnalysisReview.model_validate_json(review_json, strict=True)


def format_score(value: int | None) -> str:
    return "null" if value is None else str(value)


def effective_result_for_record(
    analysis: AnalysisResult,
    review: AnalysisReview | None,
    record,
):
    return calculate_effective_scores(
        analysis,
        review,
        analysis_revision=record["analysis_revision"],
        analysis_model=record["model"],
        prompt_version=record["prompt_version"],
    )


def list_records() -> None:
    records = fetch_recent_records(LIST_LIMIT)
    if not records:
        print("No records.")
        return

    print("ID   DATE         AI  FINAL  REVIEW      SUMMARY")
    for record in records:
        if record["analysis_json"]:
            analysis = AnalysisResult.model_validate_json(
                record["analysis_json"], strict=True
            )
            review = parse_review(record["review_json"])
            effective = effective_result_for_record(analysis, review, record)
            ai_score = format_score(analysis.overall_score)
            final_score = (
                "-"
                if effective.scores is None
                else format_score(effective.scores.overall_score)
            )
            review_state = effective.state
            summary = " ".join(analysis.summary.split())
        elif record["error_message"]:
            ai_score = "-"
            final_score = "-"
            review_state = "unreviewed"
            summary = "Analysis failed."
        else:
            ai_score = "-"
            final_score = "-"
            review_state = "unreviewed"
            summary = "Not analyzed."

        if len(summary) > 60:
            summary = f"{summary[:57]}..."
        print(
            f"{record['id']:<4} {record['entry_date']}  {ai_score:>4}  "
            f"{final_score:>5}  {review_state:<10}  {summary}"
        )


def show_record(record_id: int) -> None:
    record = fetch_record(record_id)
    if record is None:
        raise SystemExit(f"Record {record_id} not found.")

    print(f"ID: {record['id']}")
    print(f"Date: {record['entry_date']}")
    print("Text:")
    print(record["raw_text"])
    print("AI Analysis:")

    if record["analysis_json"]:
        analysis = AnalysisResult.model_validate_json(record["analysis_json"], strict=True)
        if record["model"]:
            print(f"Model: {record['model']}")
        print(f"Prompt version: {record['prompt_version'] or '-'}")
        print(f"Analysis revision: {record['analysis_revision']}")
        if record["error_message"]:
            print(f"Latest reanalysis failed: {record['error_message']}")
        print(json.dumps(analysis.model_dump(mode="json"), ensure_ascii=False, indent=2))

        review = parse_review(record["review_json"])
        effective = effective_result_for_record(analysis, review, record)
        print("User Review:")
        if review is None:
            print("Status: unreviewed")
        else:
            print(f"Status: {effective.state}")
            if effective.state == "stale":
                print(f"Stored status: {review.status}")
                print("Note: stale overrides are ignored for the current analysis.")
            print(json.dumps(review.model_dump(mode="json"), ensure_ascii=False, indent=2))

        print("Effective Scores:")
        if effective.scores is None:
            print("None (the AI analysis was rejected).")
        else:
            for field in SCORE_FIELDS:
                print(
                    f"{SCORE_LABELS[field]}: "
                    f"{format_score(getattr(effective.scores, field))}"
                )
    elif record["error_message"]:
        print(f"Failed: {record['error_message']}")
        print("User Review: unavailable until analysis succeeds.")
        print("Effective Scores: unavailable.")
    else:
        print("Not analyzed.")
        print("User Review: unavailable until analysis succeeds.")
        print("Effective Scores: unavailable.")


def display_ai_review_context(record, analysis: AnalysisResult) -> None:
    ai_scores = extract_ai_scores(analysis)
    print(f"ID: {record['id']}")
    print(f"Date: {record['entry_date']}")
    print(f"AI Summary: {analysis.summary}")
    print("AI Scores:")
    print("  SCORE                    VALUE  CONFIDENCE")
    for field in SCORE_FIELDS:
        if field == "overall_score":
            confidence = analysis.confidence
        else:
            confidence = getattr(analysis.dimensions, field).confidence
        print(
            f"  {SCORE_LABELS[field]:<24} "
            f"{format_score(getattr(ai_scores, field)):>5}  {confidence:.2f}"
        )


def display_existing_review(
    review: AnalysisReview,
    *,
    current_state: str,
) -> None:
    print("Existing User Review:")
    print(f"  Stored status: {review.status}")
    print(f"  Current state: {current_state}")
    print(f"  Reviewed at: {review.reviewed_at.isoformat()}")
    print(f"  Reason: {review.reason or '-'}")
    print("  Overrides:")
    if not review.overrides:
        print("    (none)")
    else:
        for field in SCORE_FIELDS:
            if field in review.overrides:
                print(
                    f"    {SCORE_LABELS[field]}: "
                    f"{format_score(review.overrides[field])}"
                )


def confirm_review_replacement() -> bool:
    while True:
        answer = input("Replace existing review? [y/N]: ").strip().lower()
        if answer in {"", "n", "no"}:
            return False
        if answer in {"y", "yes"}:
            return True
        print("Enter y or n.")


def choose_review_action() -> str:
    while True:
        answer = input(
            "Review [a] Accept / [e] Edit / [r] Reject / [s] Skip [a]: "
        ).strip().lower()
        if answer in {"", "a", "accept"}:
            return "accept"
        if answer in {"e", "edit"}:
            return "edit"
        if answer in {"r", "reject"}:
            return "reject"
        if answer in {"s", "skip"}:
            return "skip"
        print("Enter a, e, r, or s.")


def prompt_score_override(
    field: ScoreField,
    ai_value: int | None,
) -> tuple[bool, ScoreValue]:
    while True:
        answer = input(
            f"{SCORE_LABELS[field]} [AI: {format_score(ai_value)}] "
            "(Enter=keep, 0-100, null): "
        ).strip()
        if answer == "":
            return False, None
        if answer.lower() == "null":
            return True, None
        try:
            value = int(answer)
        except ValueError:
            print("Enter a whole number from 0 to 100, null, or press Enter.")
            continue
        if 0 <= value <= 100:
            return True, value
        print("Score must be from 0 to 100.")


def prompt_rejection_reason() -> str:
    while True:
        reason = input("Reason (required): ").strip()
        if reason:
            return reason
        print("A reason is required when rejecting an analysis.")


def review_record(record_id: int) -> None:
    record = fetch_record(record_id)
    if record is None:
        raise SystemExit(f"Record {record_id} not found.")
    if not record["analysis_json"]:
        raise SystemExit(f"Record {record_id} has no AI analysis to review.")

    analysis = AnalysisResult.model_validate_json(record["analysis_json"], strict=True)
    display_ai_review_context(record, analysis)

    existing_review = parse_review(record["review_json"])
    if existing_review is not None:
        current_state = derive_review_state(
            existing_review,
            analysis_revision=record["analysis_revision"],
            analysis_model=record["model"],
            prompt_version=record["prompt_version"],
        )
        display_existing_review(existing_review, current_state=current_state)
        if not confirm_review_replacement():
            print("Review unchanged.")
            return

    action = choose_review_action()
    if action == "skip":
        print("Skipped; no review was saved.")
        return

    overrides: dict[ScoreField, ScoreValue] = {}
    if action == "edit":
        ai_scores = extract_ai_scores(analysis)
        for field in SCORE_FIELDS:
            changed, value = prompt_score_override(field, getattr(ai_scores, field))
            if changed:
                overrides[field] = value
        status = "adjusted" if overrides else "accepted"
        reason = input("Reason (optional): ").strip()
    elif action == "reject":
        status = "rejected"
        reason = prompt_rejection_reason()
    else:
        status = "accepted"
        reason = input("Reason (optional): ").strip()

    review = create_review(
        status=status,
        overrides=overrides,
        reason=reason,
        analysis_revision=record["analysis_revision"],
        analysis_model=record["model"],
        prompt_version=record["prompt_version"],
    )
    store_review(record_id, review.model_dump_json())
    print(f"Saved {review.status} review for record {record_id}.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="kiseki",
        description="Kiseki command-line interface.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a journal record.")
    add_parser.add_argument(
        "--file",
        type=Path,
        metavar="PATH",
        help="Read journal text from a UTF-8 .md or .txt file.",
    )
    add_parser.add_argument(
        "--date",
        dest="entry_date",
        metavar="YYYY-MM-DD",
        help="Use this entry date; defaults to today in file mode.",
    )
    subparsers.add_parser("list", help="List recent journal records.")
    show_parser = subparsers.add_parser("show", help="Show one journal record.")
    show_parser.add_argument("record_id", type=int, metavar="id")
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze or reanalyze an existing journal record.",
    )
    analyze_parser.add_argument("record_id", type=int, metavar="id")
    review_parser = subparsers.add_parser(
        "review",
        help="Accept, adjust, or reject an AI analysis.",
    )
    review_parser.add_argument("record_id", type=int, metavar="id")

    args = parser.parse_args()

    if args.command == "add":
        add_record(args.file, args.entry_date)
    elif args.command == "list":
        list_records()
    elif args.command == "show":
        show_record(args.record_id)
    elif args.command == "analyze":
        analyze_record(args.record_id)
    elif args.command == "review":
        review_record(args.record_id)


if __name__ == "__main__":
    main()
