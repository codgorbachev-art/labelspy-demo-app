"""
Simple test suite for the LabelSpy demo application.

These tests utilise FastAPI's built‑in TestClient to exercise the
analysis endpoint without spinning up an external server.  They verify
that the core functions behave correctly given sample inputs.
"""

import sys
import os
from pathlib import Path

# Ensure that the package directory is on sys.path.  When this script is
# executed directly, Python might not automatically add the parent
# directory to the module search path, so we append it here.
CURRENT_DIR = Path(__file__).resolve().parent
PARENT_DIR = CURRENT_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from fastapi.testclient import TestClient
from labelspy_demo.main import app, extract_codes


def test_extract_codes_synonyms() -> None:
    """The extract_codes function should recognise synonyms defined in SYNONYMS."""
    text = "глутамат натрия, сорбиновая кислота, куркумин, L-аскорбат"
    codes = extract_codes(text)
    assert set(codes) == {"E200", "E300", "E621", "E100"}


def test_extract_codes_explicit_e_codes() -> None:
    """Explicit E‑codes with various separators should be detected."""
    text = "состав: вода, сахар, E951, e-621, e 330, e102"
    codes = extract_codes(text)
    assert set(codes) == {"E102", "E330", "E621", "E951"}


def test_analyze_endpoint_summary() -> None:
    """The /analyze endpoint should summarise the number of additives in each category."""
    client = TestClient(app)
    ingredients = (
        "вода, сахар, лимонная кислота (E330), консервант: нитрит натрия (E250), "
        "краситель тартразин (E102), аскорбиновая кислота"
    )
    response = client.get("/analyze", params={"ingredients": ingredients})
    assert response.status_code == 200
    body = response.text
    assert "1 опасных добавок" in body
    assert "1 умеренно опасных" in body
    assert "2 безопасных" in body


if __name__ == "__main__":
    # Run tests manually
    test_extract_codes_synonyms()
    test_extract_codes_explicit_e_codes()
    test_analyze_endpoint_summary()
    print("All tests passed successfully.")