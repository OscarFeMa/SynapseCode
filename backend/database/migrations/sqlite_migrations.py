"""
Idempotent SQLite migrations for local development databases.

SQLAlchemy's create_all() creates missing tables, but it intentionally does not
alter existing tables. These migrations keep older local SQLite databases
compatible with the current ORM models without dropping user data.
"""
from sqlalchemy import text
from sqlalchemy.engine import Connection


PROMPT_CACHE_TABLE = "prompt_response_cache"


def _table_exists(conn: Connection, table_name: str) -> bool:
    result = conn.execute(
        text(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name = :table_name"
        ),
        {"table_name": table_name},
    )
    return result.first() is not None


def _get_table_columns(conn: Connection, table_name: str) -> set[str]:
    rows = conn.execute(text(f"PRAGMA table_info({table_name})")).mappings()
    return {row["name"] for row in rows}


def _add_column_if_missing(
    conn: Connection,
    table_name: str,
    columns: set[str],
    column_name: str,
    column_definition: str,
) -> None:
    if column_name in columns:
        return

    conn.execute(
        text(f"ALTER TABLE {table_name} ADD COLUMN {column_definition}")
    )
    columns.add(column_name)


def _migrate_prompt_response_cache(conn: Connection) -> None:
    if not _table_exists(conn, PROMPT_CACHE_TABLE):
        return

    columns = _get_table_columns(conn, PROMPT_CACHE_TABLE)
    _add_column_if_missing(
        conn,
        PROMPT_CACHE_TABLE,
        columns,
        "prompt_embedding",
        "prompt_embedding TEXT",
    )
    _add_column_if_missing(
        conn,
        PROMPT_CACHE_TABLE,
        columns,
        "similarity_threshold",
        "similarity_threshold FLOAT NOT NULL DEFAULT 0.85",
    )
    _add_column_if_missing(
        conn,
        PROMPT_CACHE_TABLE,
        columns,
        "expires_at",
        "expires_at DATETIME",
    )

    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_prompt_cache_engine_model "
            f"ON {PROMPT_CACHE_TABLE} (engine, model)"
        )
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_prompt_cache_last_accessed "
            f"ON {PROMPT_CACHE_TABLE} (last_accessed_at)"
        )
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_prompt_cache_expires "
            f"ON {PROMPT_CACHE_TABLE} (expires_at)"
        )
    )


def _migrate_sequential_debates(conn: Connection) -> None:
    if not _table_exists(conn, "sequential_debates"):
        return

    columns = _get_table_columns(conn, "sequential_debates")
    _add_column_if_missing(
        conn,
        "sequential_debates",
        columns,
        "paused_at",
        "paused_at DATETIME",
    )
    _add_column_if_missing(
        conn,
        "sequential_debates",
        columns,
        "pause_reason",
        "pause_reason TEXT",
    )


def run_sqlite_migrations(conn: Connection) -> None:
    """Run local SQLite migrations against an existing synchronous connection."""
    if conn.dialect.name != "sqlite":
        return

    _migrate_prompt_response_cache(conn)
    _migrate_sequential_debates(conn)
