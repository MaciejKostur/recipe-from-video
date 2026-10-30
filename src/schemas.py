"""Struktura przepisu zwracana przez model i zapisywana w bazie."""
from pydantic import BaseModel


class Ingredient(BaseModel):
    name: str
    amount: str | None = None


class Recipe(BaseModel):
    name: str
    time_minutes: int | None = None
    servings: int | None = None
    ingredients: list[Ingredient]
    steps: list[str]
    tips: list[str] = []
