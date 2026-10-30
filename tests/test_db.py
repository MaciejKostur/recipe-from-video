import sqlite3

import pytest

from schemas import Ingredient, Recipe


def make_recipe(name="Jajecznica", ingredients=None, steps=None):
    return Recipe(
        name=name,
        time_minutes=10,
        servings=1,
        ingredients=ingredients
        or [Ingredient(name="Jajka", amount="3"), Ingredient(name="Śmietanka", amount="2 łyżki")],
        steps=steps or ["Rozgrzej patelnię.", "Wbij jajka."],
        tips=["Nie smaż za długo."],
    )


def test_save_and_get_roundtrip(temp_db):
    rid = temp_db.save_recipe(make_recipe(), "https://www.youtube.com/watch?v=AAAAAAAAAAA")
    data = temp_db.get_recipe(rid)
    assert data["recipe"]["name"] == "Jajecznica"
    assert [i["name"] for i in data["ingredients"]] == ["jajka", "śmietanka"]
    assert data["steps"] == ["Rozgrzej patelnię.", "Wbij jajka."]


def test_get_missing_recipe_returns_none(temp_db):
    assert temp_db.get_recipe(999) is None


def test_duplicate_source_url_is_rejected(temp_db):
    url = "https://www.youtube.com/watch?v=AAAAAAAAAAA"
    rid = temp_db.save_recipe(make_recipe(), url)
    assert temp_db.recipe_exists(url) == rid
    with pytest.raises(sqlite3.IntegrityError):
        temp_db.save_recipe(make_recipe(), url)


def test_failed_save_leaves_no_orphans(temp_db):
    url = "https://www.youtube.com/watch?v=AAAAAAAAAAA"
    temp_db.save_recipe(make_recipe(), url)
    with pytest.raises(sqlite3.IntegrityError):
        temp_db.save_recipe(make_recipe(name="Drugi"), url)
    with temp_db.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM recipes").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM ingredients").fetchone()[0] == 2


def test_search_is_case_insensitive_for_polish_letters(temp_db):
    temp_db.save_recipe(make_recipe(), "https://www.youtube.com/watch?v=AAAAAAAAAAA")
    assert len(temp_db.search_by_ingredient("ŚMIETANKA")) == 1
    assert len(temp_db.search_by_ingredient("śmiet")) == 1
    assert temp_db.search_by_ingredient("kurczak") == []
    assert temp_db.search_by_ingredient("   ") == []


def test_search_treats_like_wildcards_as_text(temp_db):
    temp_db.save_recipe(make_recipe(), "https://www.youtube.com/watch?v=AAAAAAAAAAA")
    assert temp_db.search_by_ingredient("%") == []
    assert temp_db.search_by_ingredient("_") == []


def test_sql_injection_payload_is_harmless(temp_db):
    temp_db.save_recipe(make_recipe(), "https://www.youtube.com/watch?v=AAAAAAAAAAA")
    assert temp_db.search_by_ingredient("'; DROP TABLE recipes; --") == []
    assert len(temp_db.list_recipes()) == 1

    evil = make_recipe(name="x'); DROP TABLE recipes; --")
    rid = temp_db.save_recipe(evil, "https://www.youtube.com/watch?v=BBBBBBBBBBB")
    assert temp_db.get_recipe(rid)["recipe"]["name"] == "x'); DROP TABLE recipes; --"
    assert len(temp_db.list_recipes()) == 2


def test_delete_cascades_to_children(temp_db):
    rid = temp_db.save_recipe(make_recipe(), "https://www.youtube.com/watch?v=AAAAAAAAAAA")
    assert temp_db.delete_recipe(rid) is True
    assert temp_db.delete_recipe(rid) is False
    with temp_db.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM ingredients").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM steps").fetchone()[0] == 0


def test_oversized_model_output_is_truncated(temp_db):
    huge = make_recipe(
        name="N" * 1000,
        ingredients=[Ingredient(name=f"skladnik{i}", amount="1") for i in range(500)],
        steps=["krok " * 1000] * 200,
    )
    rid = temp_db.save_recipe(huge, "https://www.youtube.com/watch?v=AAAAAAAAAAA")
    data = temp_db.get_recipe(rid)
    assert len(data["recipe"]["name"]) == temp_db.MAX_NAME
    assert len(data["ingredients"]) == temp_db.MAX_INGREDIENTS
    assert len(data["steps"]) == temp_db.MAX_STEPS
    assert all(len(s) <= temp_db.MAX_STEP_TEXT for s in data["steps"])
