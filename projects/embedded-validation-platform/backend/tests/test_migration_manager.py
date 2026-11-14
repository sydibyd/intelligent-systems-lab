from unittest.mock import MagicMock, patch

import pytest

from migration_manager import apply_migrations


def test_apply_migration(tmp_path):
    migration = tmp_path / "001_test.sql"
    migration.write_text("SELECT 1;")

    db = MagicMock()

    with patch("migration_manager.MIGRATIONS_DIR", tmp_path):
        with patch("migration_manager.psycopg.connect") as connect:
            connect.return_value.__enter__.return_value = db

            result = apply_migrations()

    assert result == ["001_test.sql"]
    assert connect.call_args.kwargs["autocommit"] is True

    db.execute.assert_called_once_with(
        "SELECT 1;",
        prepare=False
    )


def test_migration_execution_order(tmp_path):
    (tmp_path / "002_second.sql").write_text("SELECT 2;")
    (tmp_path / "001_first.sql").write_text("SELECT 1;")

    db = MagicMock()

    with patch("migration_manager.MIGRATIONS_DIR", tmp_path):
        with patch("migration_manager.psycopg.connect") as connect:
            connect.return_value.__enter__.return_value = db

            result = apply_migrations()

    assert result == [
        "001_first.sql",
        "002_second.sql"
    ]

    assert [
        call.args[0]
        for call in db.execute.call_args_list
    ] == ["SELECT 1;", "SELECT 2;"]


def test_missing_migrations(tmp_path):
    with patch("migration_manager.MIGRATIONS_DIR", tmp_path):
        with pytest.raises(
            RuntimeError,
            match="No database migrations found"
        ):
            apply_migrations()


def test_database_error_propagation(tmp_path):
    (tmp_path / "001_test.sql").write_text("INVALID SQL;")

    db = MagicMock()
    db.execute.side_effect = RuntimeError("Database error")

    with patch("migration_manager.MIGRATIONS_DIR", tmp_path):
        with patch("migration_manager.psycopg.connect") as connect:
            connect.return_value.__enter__.return_value = db

            with pytest.raises(
                RuntimeError,
                match="Database error"
            ):
                apply_migrations()
