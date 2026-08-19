import argparse
import json
import sqlite3
from datetime import date
from pathlib import Path

from model import analyze_entry
from schema import AnalysisResult


DATABASE_PATH = Path(__file__).resolve().parent / "data" / "kiseki.db"
LIST_LIMIT = 20


def open_database() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date TEXT NOT NULL,
            raw_text TEXT NOT NULL,
            model TEXT,
            analysis_json TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(daily_records)")
    }
    if "model" not in columns:
        connection.execute("ALTER TABLE daily_records ADD COLUMN model TEXT")
    if "analysis_json" not in columns:
        connection.execute("ALTER TABLE daily_records ADD COLUMN analysis_json TEXT")
    if "error_message" not in columns:
        connection.execute("ALTER TABLE daily_records ADD COLUMN error_message TEXT")
    return connection


def add_record() -> None:
    today = date.today().isoformat()
    entered_date = input(f"Date [{today}]: ").strip() or today

    try:
        entry_date = date.fromisoformat(entered_date).isoformat()
    except ValueError as error:
        raise SystemExit("Date must use YYYY-MM-DD format.") from error

    raw_text = input("Text: ")
    if not raw_text.strip():
        raise SystemExit("Text cannot be empty.")

    with open_database() as connection:
        cursor = connection.execute(
            "INSERT INTO daily_records (entry_date, raw_text) VALUES (?, ?)",
            (entry_date, raw_text),
        )
        record_id = cursor.lastrowid

    print(f"Saved record {record_id}.")

    try:
        model_name, analysis = analyze_entry(entry_date, raw_text)
    except Exception as error:
        with open_database() as connection:
            connection.execute(
                "UPDATE daily_records SET error_message = ? WHERE id = ?",
                (str(error), record_id),
            )
        raise SystemExit(f"Analysis failed for record {record_id}: {error}") from error

    with open_database() as connection:
        connection.execute(
            """
            UPDATE daily_records
            SET model = ?, analysis_json = ?, error_message = NULL
            WHERE id = ?
            """,
            (model_name, analysis.model_dump_json(), record_id),
        )

    score = "null" if analysis.overall_score is None else analysis.overall_score
    print(f"Overall score: {score}")
    print(f"Summary: {analysis.summary}")
    print(f"Confidence: {analysis.confidence:.2f}")


def list_records() -> None:
    with open_database() as connection:
        records = connection.execute(
            """
            SELECT id, entry_date, analysis_json, error_message
            FROM daily_records
            ORDER BY entry_date DESC, id DESC
            LIMIT ?
            """,
            (LIST_LIMIT,),
        ).fetchall()

    if not records:
        print("No records.")
        return

    print("ID   DATE        SCORE  SUMMARY")
    for record in records:
        if record["analysis_json"]:
            analysis = AnalysisResult.model_validate_json(
                record["analysis_json"], strict=True
            )
            score = "null" if analysis.overall_score is None else str(analysis.overall_score)
            summary = " ".join(analysis.summary.split())
        elif record["error_message"]:
            score = "-"
            summary = "Analysis failed."
        else:
            score = "-"
            summary = "Not analyzed."

        if len(summary) > 60:
            summary = f"{summary[:57]}..."
        print(f"{record['id']:<4} {record['entry_date']}  {score:>5}  {summary}")


def show_record(record_id: int) -> None:
    with open_database() as connection:
        record = connection.execute(
            """
            SELECT id, entry_date, raw_text, model, analysis_json, error_message
            FROM daily_records
            WHERE id = ?
            """,
            (record_id,),
        ).fetchone()

    if record is None:
        raise SystemExit(f"Record {record_id} not found.")

    print(f"ID: {record['id']}")
    print(f"Date: {record['entry_date']}")
    print("Text:")
    print(record["raw_text"])
    print("Analysis:")

    if record["analysis_json"]:
        analysis = AnalysisResult.model_validate_json(record["analysis_json"], strict=True)
        if record["model"]:
            print(f"Model: {record['model']}")
        print(json.dumps(analysis.model_dump(mode="json"), ensure_ascii=False, indent=2))
    elif record["error_message"]:
        print(f"Failed: {record['error_message']}")
    else:
        print("Not analyzed.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="kiseki",
        description="Kiseki command-line interface.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("add", help="Add a journal record.")
    subparsers.add_parser("list", help="List recent journal records.")
    show_parser = subparsers.add_parser("show", help="Show one journal record.")
    show_parser.add_argument("record_id", type=int, metavar="id")

    args = parser.parse_args()

    if args.command == "add":
        add_record()
    elif args.command == "list":
        list_records()
    else:
        show_record(args.record_id)


if __name__ == "__main__":
    main()
