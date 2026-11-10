from sqlalchemy import text

from app.core.database import engine


def test_sqlite_uses_wal_mode() -> None:
    with engine.connect() as connection:
        journal_mode = connection.execute(text("PRAGMA journal_mode;")).scalar_one()
        synchronous = connection.execute(text("PRAGMA synchronous;")).scalar_one()
        foreign_keys = connection.execute(text("PRAGMA foreign_keys;")).scalar_one()

    assert str(journal_mode).lower() == "wal"
    # synchronous=NORMAL se representa como 1.
    assert int(synchronous) == 1
    assert int(foreign_keys) == 1
