"""
Integration tests for SQLite migrations
"""

from sqlalchemy import create_engine, text

from backend.database.migrations.sqlite_migrations import run_sqlite_migrations


class TestSqliteMigrations:
    """Pruebas de migraciones SQLite"""

    def test_sqlite_migration_upgrades_legacy_prompt_cache_schema(self):
        engine = create_engine("sqlite:///:memory:")

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE prompt_response_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        cache_key VARCHAR(64) NOT NULL UNIQUE,
                        engine VARCHAR(20) NOT NULL,
                        model VARCHAR(100) NOT NULL,
                        node VARCHAR(20) NOT NULL,
                        temperature FLOAT NOT NULL DEFAULT 0.0,
                        max_tokens INTEGER,
                        prompt_hash VARCHAR(64) NOT NULL,
                        response_text TEXT NOT NULL,
                        tokens_in INTEGER NOT NULL DEFAULT 0,
                        tokens_out INTEGER NOT NULL DEFAULT 0,
                        latency_ms INTEGER NOT NULL DEFAULT 0,
                        hit_count INTEGER NOT NULL DEFAULT 0,
                        created_at DATETIME NOT NULL,
                        last_accessed_at DATETIME NOT NULL
                    )
                    """
                )
            )

            run_sqlite_migrations(conn)
            run_sqlite_migrations(conn)

            columns = {row._mapping["name"] for row in conn.execute(text("PRAGMA table_info(prompt_response_cache)"))}
            indexes = {row._mapping["name"] for row in conn.execute(text("PRAGMA index_list(prompt_response_cache)"))}

        assert {"prompt_embedding", "similarity_threshold", "expires_at"} <= columns
        assert "idx_prompt_cache_expires" in indexes

    def test_sqlite_migration_exists(self):
        assert callable(run_sqlite_migrations)
