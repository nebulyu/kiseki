import argparse
import json
import sqlite3
from datetime import date
from pathlib import Path

from model import analyze_entry
from schema import AnalysisResult


DATABASE_PATH = Path(__file__).resolve().parent / "data" / "kiseki.db"
LIST_LIMIT = 20
SUPPORTED_ENTRY_SUFFIXES = {".md", ".txt"}


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

    args = parser.parse_args()

    if args.command == "add":
        add_record(args.file, args.entry_date)
    elif args.command == "list":
        list_records()
    else:
        show_record(args.record_id)


if __name__ == "__main__":
    main()
