"""Recipe from Video: aplikacja konsolowa (menu)."""
from dotenv import load_dotenv

load_dotenv()

import db  # noqa: E402
import llm  # noqa: E402
from security import sanitize_text, validate_youtube_url  # noqa: E402


def print_recipe(data):
    r = data["recipe"]
    print(f"\n## {r['name']}  (id: {r['id']})")
    print(f"Czas: {r['time_minutes'] or '?'} min | Porcje: {r['servings'] or '?'}")
    print("\nSkładniki:")
    for i in data["ingredients"]:
        print(f"- {i['name']}: {i['amount'] or 'nie podano'}")
    print("\nPrzygotowanie:")
    for n, step in enumerate(data["steps"], 1):
        print(f"{n}. {step}")
    if r["tips"]:
        print(f"\nWskazówki:\n{r['tips']}")
    print(f"\nŹródło: {r['source_url']}")


def show_rows(rows):
    if not rows:
        print("Brak wyników.")
        return
    for r in rows:
        print(f"[{r['id']}] {r['name']} ({r['time_minutes'] or '?'} min)")


def ask_id(prompt="Podaj id: "):
    raw = input(prompt).strip()
    return int(raw) if raw.isdigit() else None


def add_recipe_flow():
    url = validate_youtube_url(input("Wklej link do filmu z YouTube: "))
    if url is None:
        print("To nie jest poprawny link do YouTube (youtube.com/watch, youtu.be, Shorts).")
        return

    existing_id = db.recipe_exists(url)
    if existing_id:
        print(f"Ten przepis już masz zapisany (id: {existing_id}). Nie zużywam limitu API.")
        print_recipe(db.get_recipe(existing_id))
        return

    print("\nAnalizuję film, to może potrwać kilkanaście sekund...")
    try:
        recipe = llm.extract_recipe(url)
    except RuntimeError as e:
        print(e)
        return
    if recipe is None:
        print("Nie udało się pobrać przepisu.")
        return

    recipe_id = db.save_recipe(recipe, url)
    print(f"Zapisano przepis (id: {recipe_id}).")
    print_recipe(db.get_recipe(recipe_id))


def main():
    db.init_db()
    if llm.is_demo():
        print("*** TRYB DEMO: API Gemini jest pomijane ***")
    while True:
        print(
            "\n1. Dodaj przepis z filmu\n2. Lista przepisów\n3. Pokaż przepis (id)"
            "\n4. Szukaj po składniku\n5. Usuń przepis (id)\n0. Wyjście"
        )
        choice = input("Wybierz: ").strip()
        if choice == "1":
            add_recipe_flow()
        elif choice == "2":
            show_rows(db.list_recipes())
        elif choice == "3":
            recipe_id = ask_id()
            data = db.get_recipe(recipe_id) if recipe_id else None
            print_recipe(data) if data else print("Nie ma takiego przepisu.")
        elif choice == "4":
            show_rows(db.search_by_ingredient(sanitize_text(input("Składnik: "), 50)))
        elif choice == "5":
            recipe_id = ask_id()
            ok = db.delete_recipe(recipe_id) if recipe_id else False
            print("Usunięto." if ok else "Nie ma takiego przepisu.")
        elif choice == "0":
            break
        else:
            print("Nieznana opcja.")


if __name__ == "__main__":
    main()
