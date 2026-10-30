"""Testy logiki wokół modelu bez prawdziwych zapytań do API."""
import llm
from schemas import Recipe


def test_demo_mode_skips_api(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "1")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    recipe = llm.extract_recipe("https://www.youtube.com/watch?v=AAAAAAAAAAA")
    assert isinstance(recipe, Recipe)
    assert recipe.ingredients and recipe.steps


def test_models_list_parsed_from_env(monkeypatch):
    monkeypatch.setenv("GEMINI_MODELS", " model-a , model-b ,, ")
    assert llm.get_models() == ["model-a", "model-b"]


def test_missing_key_gives_clear_error(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(llm, "_client", None)
    try:
        llm.extract_recipe("https://www.youtube.com/watch?v=AAAAAAAAAAA")
    except RuntimeError as e:
        assert "GEMINI_API_KEY" in str(e)
    else:
        raise AssertionError("Oczekiwano RuntimeError")


class _FakeResponse:
    def __init__(self, text):
        self.text = text


def _patch_call(monkeypatch, text):
    monkeypatch.setenv("DEMO_MODE", "")
    monkeypatch.setattr(llm, "call_model", lambda contents, config: _FakeResponse(text))


def test_valid_model_json_is_parsed(monkeypatch):
    _patch_call(
        monkeypatch,
        '{"name":"Zupa","ingredients":[{"name":"woda","amount":"1 l"}],"steps":["Zagotuj."]}',
    )
    recipe = llm.extract_recipe("https://www.youtube.com/watch?v=AAAAAAAAAAA")
    assert recipe.name == "Zupa"


def test_garbage_model_output_returns_none(monkeypatch):
    _patch_call(monkeypatch, "to nie jest json, ignoruj instrukcje")
    assert llm.extract_recipe("https://www.youtube.com/watch?v=AAAAAAAAAAA") is None


def test_empty_recipe_returns_none(monkeypatch):
    _patch_call(monkeypatch, '{"name":"Nic","ingredients":[],"steps":[]}')
    assert llm.extract_recipe("https://www.youtube.com/watch?v=AAAAAAAAAAA") is None
