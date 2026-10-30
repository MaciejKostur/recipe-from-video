# Recipe from Video

Aplikacja konsolowa w Pythonie: wklejasz link do filmu kulinarnego z YouTube,
model Gemini wyciąga z niego przepis, a program zapisuje go w lokalnej bazie
SQLite i pozwala wyszukiwać przepisy po składnikach.

**Obszar:** aplikacje z LLM / multimodalne API / bezpieczne przetwarzanie danych.
Projekt edukacyjny, budowany od zera przy nauce pracy z API modeli językowych.

## Status

| Element | Stan |
|---|---|
| Baza SQLite, wyszukiwanie, usuwanie, menu | działa, pokryte testami (`pytest`) |
| Walidacja linków i danych od modelu | działa, pokryta testami |
| Tryb DEMO (bez klucza API) | działa |
| Analiza filmu przez Gemini API | **zaimplementowana, ale niezweryfikowana end-to-end** |

W trakcie prac darmowy model Gemini zwracał błędy przeciążenia (503) i limitów
(429), więc prawdziwe wywołanie z filmem nie zostało jeszcze potwierdzone.
Logika wokół modelu (parsowanie, walidacja, obsługa błędów) jest testowana na
atrapach odpowiedzi.

## Uruchomienie

```bash
git clone <adres-repo>
cd recipe-from-video
python -m venv venv
venv\Scripts\activate          # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
python src/main.py
```

**Bez klucza (tryb DEMO):** ustaw zmienną `DEMO_MODE=1`
(PowerShell: `$env:DEMO_MODE="1"`). Program zwróci przykładowy przepis.

**Z prawdziwym API:** skopiuj `.env.example` do `.env`, wpisz klucz z
[aistudio.google.com](https://aistudio.google.com) i ewentualnie listę modeli w
`GEMINI_MODELS` (nazwy sprawdzisz poleceniem `python src/list_models.py`).

**Testy:** `pytest`

## Struktura

```
recipe-from-video/
├── src/
│   ├── main.py          # menu konsolowe
│   ├── llm.py           # Gemini: film -> przepis, zapasowe modele, tryb DEMO
│   ├── db.py            # SQLite: zapis, wyszukiwanie, usuwanie
│   ├── schemas.py       # modele Pydantic (Recipe, Ingredient)
│   ├── security.py      # walidacja linków YouTube, czyszczenie tekstu
│   └── list_models.py   # pomocnik: lista dostępnych modeli
├── tests/               # testy pytest (baza, walidacja, logika LLM)
├── data/                # tu powstaje recipes.db (poza repozytorium)
├── .env.example
├── requirements.txt
└── README.md
```

## Jak to działa

Link do YouTube -> walidacja -> Gemini (film + schemat JSON) -> walidacja
Pydantic -> zapis w SQLite (`recipes`, `ingredients`, `steps`).
Ten sam film nie jest analizowany drugi raz (kolumna `source_url UNIQUE`),
co oszczędza limit API.

## Zagrożenia i zabezpieczenia

- **Walidacja linku:** tylko `youtube.com`, `youtu.be` i Shorts. Adres jest
  budowany od nowa z 11-znakowego ID, więc do modelu nie trafia dowolny URL.
  Testy obejmują m.in. `youtube.com.evil.com`, `youtube.com@evil.com`,
  schematy `javascript:` i `file:`.
- **Dane od modelu są niezaufane:** walidacja Pydantic, limity długości i liczby
  elementów przed zapisem.
- **SQL injection:** wszystkie zapytania są parametryzowane; test sprawdza
  payload `'; DROP TABLE ...`. Znaki specjalne `LIKE` są traktowane jak tekst.
- **Integralność danych:** zapis przepisu w jednej transakcji, klucze obce
  z `ON DELETE CASCADE`.
- **Prompt injection (głos lub opis w filmie):** prompt każe traktować treść
  filmu jako dane, a odpowiedź musi przejść walidację schematu. To ograniczenie,
  nie gwarancja; nie testowałem go na prawdziwych filmach.
- **Sekrety:** klucz w `.env` (poza repozytorium), plik bazy w `.gitignore`.
- **Prywatność:** w darmowym planie Gemini wysyłane treści mogą być używane do
  ulepszania produktów Google; nie wysyłaj danych poufnych.
- **Prawa autorskie:** przepis jest zapisywany własnymi słowami modelu,
  razem z linkiem do filmu.

## Ograniczenia

- Tylko publiczne filmy z YouTube (Instagram, TikTok i Facebook nie są obsługiwane).
- Jakość zależy od tego, co autor filmu pokazuje i mówi; brakujące ilości są
  oznaczane jako "nie podano w filmie".
- Darmowy plan API ma niskie i zmienne limity.

## Czego się nauczyłem

- Praca z API LLM: błędy 429/503, ponawianie, przełączanie na zapasowe modele.
- Darmowe plany i modele zmieniają się szybko: model 2.5 przestał być dostępny
  dla nowych kont w trakcie projektu, a darmowe wyszukiwanie Google okazało się
  niedostępne, więc zmieniłem koncepcję na analizę filmu.
- Wymuszanie ustrukturyzowanej odpowiedzi (JSON + Pydantic).
- Projektowanie bazy SQL z relacjami, transakcjami i testami bezpieczeństwa.
- Testowanie kodu zależnego od zewnętrznego API przy pomocy atrap.

## Plany

- Test end-to-end na prawdziwym filmie, gdy API będzie dostępne
- Dopasowanie zapisanych przepisów do składników z lodówki
- Eksport przepisu do pliku i listy zakupów
