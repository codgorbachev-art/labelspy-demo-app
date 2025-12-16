"""
LabelSpy Demo Application

This FastAPI application implements a simplified demo of the LabelSpy
service described in the provided business plan.  The goal of the demo is
to showcase the core user journey — extraction of ingredient lists,
normalization of food additive identifiers and safety classification.

The implementation deliberately avoids calling external AI services and
instead relies on simple pattern matching and a small, curated knowledge
base.  In a production system the OCR and entity recognition steps would
be powered by multimodal models such as GPT‑4o mini Vision or Yandex
Vision OCR followed by a large language model for normalisation.  The
demo, however, follows the same three‑stage architecture articulated in
the business plan: 1) obtain the ingredient text, 2) normalise
additives to a canonical E‑code and 3) verify each code against a
symbolic knowledge base to assign a colour‑coded safety rating【249004782706408†L175-L221】.

The web interface allows the user to paste an ingredient list.  On
submission it extracts any known E‑codes or their synonyms, looks them
up in the bundled knowledge base, counts the number of green/yellow/red
additives and displays a short summary alongside a detailed table.
"""

import json
import re
from pathlib import Path
from typing import Dict, List

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Create the FastAPI app
app = FastAPI(title="LabelSpy Demo")

# Set up templates and static files directory
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Load the E‑code knowledge base
DATA_PATH = BASE_DIR / "data" / "e_codes.json"
with open(DATA_PATH, encoding="utf-8") as f:
    E_CODE_DB: Dict[str, Dict[str, str]] = json.load(f)

# Define a small dictionary of synonyms to canonical E‑codes
# In a full implementation this would be generated via an LLM with few‑shot
# prompting【249004782706408†L182-L207】.  Here we capture a handful of common Russian
# names for well known additives.  All keys should be lower‑case.
SYNONYMS: Dict[str, str] = {
    "аскорбиновая кислота": "E300",
    "l-аскорбат": "E300",
    "глутамат натрия": "E621",
    "глутамат мононатрия": "E621",
    "моноглутамат натрия": "E621",
    "асpartame": "E951",
    "аспартам": "E951",
    "нитрит натрия": "E250",
    "сорбиновая кислота": "E200",
    "куркумин": "E100",
    "лимонная кислота": "E330",
}


def extract_codes(text: str) -> List[str]:
    """Extract canonical E‑codes from a free‑form ingredient list.

    This function performs two passes over the input:  first, it looks
    for any synonyms defined in the SYNONYMS dictionary and records the
    corresponding codes.  Second, it finds explicit E‑codes in the text
    using a regular expression.  Codes are normalised to the pattern
    "E###" regardless of case or whitespace.
    """
    found: set[str] = set()
    lower_text = text.lower()

    # Search for synonyms (case‑insensitive)
    for syn, code in SYNONYMS.items():
        if syn in lower_text:
            found.add(code)

    # Find patterns such as "E102", "e‑102", or "e 102"
    for match in re.findall(r"e\s*-?\s*\d{3}", lower_text):
        digits = re.search(r"\d{3}", match)
        if digits:
            found.add(f"E{digits.group()}")

    return sorted(found)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Render the home page with an input form for the ingredient list."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
        },
    )


@app.get("/analyze", response_class=HTMLResponse)
async def analyze(request: Request, ingredients: str = "") -> HTMLResponse:
    """
    Handle ingredient analysis via a query parameter.  Since the environment
    lacks the python‑multipart library, we avoid using `Form` and instead
    accept the ingredient list as a plain query string.  The `index.html`
    template submits its form with method="get" so that the input appears
    in the URL as `?ingredients=...`.
    """
    # Trim whitespace from the input; if empty render a simple page
    ingredients = ingredients.strip()
    if not ingredients:
        return templates.TemplateResponse(
            "result.html",
            {
                "request": request,
                "results": [],
                "summary": "Не найдено известных добавок.",
                "counts": {"green": 0, "yellow": 0, "red": 0, "unknown": 0},
            },
        )

    codes = extract_codes(ingredients)
    results: List[Dict[str, str]] = []
    counts = {"green": 0, "yellow": 0, "red": 0, "unknown": 0}

    for code in codes:
        record = E_CODE_DB.get(code.upper())
        if record:
            category = record.get("category", "unknown")
        else:
            category = "unknown"
            record = {"name": "", "description": "Неизвестный код", "category": category}
        counts[category] = counts.get(category, 0) + 1
        results.append({"code": code, **record})

    # Compose summary message in Russian
    summary_parts = []
    if counts["red"]:
        summary_parts.append(f"{counts['red']} опасных добавок")
    if counts["yellow"]:
        summary_parts.append(f"{counts['yellow']} умеренно опасных")
    if counts["green"]:
        summary_parts.append(f"{counts['green']} безопасных")
    if not summary_parts:
        summary_message = "Не найдено известных добавок."
    else:
        summary_message = "Найдено " + ", ".join(summary_parts) + "."

    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "results": results,
            "summary": summary_message,
            "counts": counts,
        },
    )