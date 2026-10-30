"""Warstwa bazy danych (SQLite). Wszystkie zapytania są parametryzowane."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from schemas import Recipe

DB_PATH = Path(
    os.getenv("RECIPES_DB")
    or Path(__file__).resolve().parent.parent / "data" / "recipes.db"
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    time_minutes INTEGER,
    servings INTEGER,
    source_url TEXT NOT NULL UNIQUE,
    tips TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    amount TEXT
);
CREATE TABLE IF NOT EXISTS steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ingredients_recipe ON ingredients(recipe_id);
CREATE INDEX IF NOT EXISTS idx_steps_recipe ON steps(recipe_id);
"""

# Limity długości: dane z modelu traktujemy jak niezaufane.
MAX_NAME = 150
MAX_INGREDIENTS = 60
MAX_INGREDIENT_NAME = 100
MAX_AMOUNT = 50
MAX_STEPS = 40
MAX_STEP_TEXT = 1000
MAX_TIPS = 1000


def _pl_lower(value):
    # SQLite lower() obsługuje tylko ASCII, więc "Śmietanka" wymaga własnej funkcji.
    return value.casefold() if isinstance(value, str) else value


@contextmanager
def connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.create_function("pl_lower", 1, _pl_lower)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connection() as conn:
        conn.executescript(SCHEMA)


def recipe_exists(source_url: str):
    with connection() as conn:
        row = conn.execute(
            "SELECT id FROM recipes WHERE source_url = ?", (source_url,)
        ).fetchone()
    return row["id"] if row else None


def save_recipe(recipe: Recipe, source_url: str) -> int:
    """Zapisuje przepis w jednej transakcji i zwraca jego id."""
    with connection() as conn:
        cur = conn.execute(
            "INSERT INTO recipes (name, time_minutes, servings, source_url, tips) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                recipe.name.strip()[:MAX_NAME],
                recipe.time_minutes,
                recipe.servings,
                source_url,
                "\n".join(recipe.tips)[:MAX_TIPS],
            ),
        )
        recipe_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO ingredients (recipe_id, name, amount) VALUES (?, ?, ?)",
            [
                (
                    recipe_id,
                    i.name.strip().lower()[:MAX_INGREDIENT_NAME],
                    (i.amount or "")[:MAX_AMOUNT],
                )
                for i in recipe.ingredients[:MAX_INGREDIENTS]
            ],
        )
        conn.executemany(
            "INSERT INTO steps (recipe_id, position, text) VALUES (?, ?, ?)",
            [
                (recipe_id, n, s.strip()[:MAX_STEP_TEXT])
                for n, s in enumerate(recipe.steps[:MAX_STEPS], 1)
            ],
        )
    return recipe_id


def list_recipes():
    with connection() as conn:
        rows = conn.execute(
            "SELECT id, name, time_minutes FROM recipes ORDER BY id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def search_by_ingredient(term: str):
    term = term.strip().casefold()
    if not term:
        return []
    # Znaki specjalne LIKE traktujemy jako zwykły tekst.
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    with connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT r.id, r.name, r.time_minutes FROM recipes r "
            "JOIN ingredients i ON i.recipe_id = r.id "
            "WHERE pl_lower(i.name) LIKE ? ESCAPE '\\' ORDER BY r.id DESC",
            (f"%{escaped}%",),
        ).fetchall()
    return [dict(r) for r in rows]


def get_recipe(recipe_id: int):
    with connection() as conn:
        recipe = conn.execute(
            "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
        ).fetchone()
        if recipe is None:
            return None
        ingredients = conn.execute(
            "SELECT name, amount FROM ingredients WHERE recipe_id = ? ORDER BY id",
            (recipe_id,),
        ).fetchall()
        steps = conn.execute(
            "SELECT text FROM steps WHERE recipe_id = ? ORDER BY position",
            (recipe_id,),
        ).fetchall()
    return {
        "recipe": dict(recipe),
        "ingredients": [dict(i) for i in ingredients],
        "steps": [s["text"] for s in steps],
    }


def delete_recipe(recipe_id: int) -> bool:
    """Usuwa przepis; składniki i kroki znikają kaskadowo."""
    with connection() as conn:
        cur = conn.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    return cur.rowcount > 0
