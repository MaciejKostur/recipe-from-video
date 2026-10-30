import pytest

import db


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Każdy test dostaje świeżą, pustą bazę w katalogu tymczasowym."""
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    return db
