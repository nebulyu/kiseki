import sqlite3
from contextlib import closing
from pathlib import Path


DATABASE_PATH = Path(__file__).resolve().parent / "data" / "kiseki.db"


def open_database(database_path: Path = DATABASE_PATH) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
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
            prompt_version TEXT,
            analysis_revision INTEGER NOT NULL DEFAULT 0,
            review_json TEXT,
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
    if "prompt_version" not in columns:
        connection.execute("ALTER TABLE daily_records ADD COLUMN prompt_version TEXT")
    if "analysis_revision" not in columns:
        connection.execute(
            "ALTER TABLE daily_records "
            "ADD COLUMN analysis_revision INTEGER NOT NULL DEFAULT 0"
        )
    if "review_json" not in columns:
        connection.execute("ALTER TABLE daily_records ADD COLUMN review_json TEXT")
    connection.commit()
    return connection


def insert_record(
    entry_date: str,
    raw_text: str,
    database_path: Path = DATABASE_PATH,
) -> int:
    with closing(open_database(database_path)) as connection, connection:
        cursor = connection.execute(
            "INSERT INTO daily_records (entry_date, raw_text) VALUES (?, ?)",
            (entry_date, raw_text),
        )
        return int(cursor.lastrowid)


def store_analysis_error(
    record_id: int,
    error_message: str,
    database_path: Path = DATABASE_PATH,
) -> None:
    with closing(open_database(database_path)) as connection, connection:
        connection.execute(
            "UPDATE daily_records SET error_message = ? WHERE id = ?",
            (error_message, record_id),
        )


def store_analysis(
    record_id: int,
    *,
    model: str,
    analysis_json: str,
    prompt_version: str,
    database_path: Path = DATABASE_PATH,
) -> None:
    with closing(open_database(database_path)) as connection, connection:
        connection.execute(
            """
            UPDATE daily_records
            SET model = ?,
                analysis_json = ?,
                error_message = NULL,
                prompt_version = ?,
                analysis_revision = analysis_revision + 1
            WHERE id = ?
            """,
            (model, analysis_json, prompt_version, record_id),
        )


def fetch_recent_records(
    limit: int,
    database_path: Path = DATABASE_PATH,
) -> list[sqlite3.Row]:
    with closing(open_database(database_path)) as connection:
        return connection.execute(
            """
            SELECT id, entry_date, model, analysis_json, error_message,
                   prompt_version, analysis_revision, review_json
            FROM daily_records
            ORDER BY entry_date DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()


def fetch_record(
    record_id: int,
    database_path: Path = DATABASE_PATH,
) -> sqlite3.Row | None:
    with closing(open_database(database_path)) as connection:
        return connection.execute(
            """
            SELECT id, entry_date, raw_text, model, analysis_json, error_message,
                   prompt_version, analysis_revision, review_json, created_at
            FROM daily_records
            WHERE id = ?
            """,
            (record_id,),
        ).fetchone()


def store_review(
    record_id: int,
    review_json: str,
    database_path: Path = DATABASE_PATH,
) -> None:
    with closing(open_database(database_path)) as connection, connection:
        connection.execute(
            "UPDATE daily_records SET review_json = ? WHERE id = ?",
            (review_json, record_id),
        )
