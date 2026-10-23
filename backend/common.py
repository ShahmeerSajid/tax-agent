"""
This file holds the small shared helpers that every other tax module uses, so
that the logic modules and the tool registry (tools.py) never repeat each
other. It loads the tax rules (from the JSON file by default, or from the Neon
database when RULES_SOURCE=db is set in .env) and the verified parameter file
data/tax_parameters_2026.json, which stores only figures read from official
Government of Canada pages together with their source links. It also validates
inputs (amounts must be finite and not negative, years must be whole numbers
in a sensible range), turns a city, a province name or a code into the
two-letter jurisdiction code, and lists the known limits of the calculator.

We need this because the whole project depends on one rule: the AI never does
tax math and never invents a number. Putting validation, province matching and
result labelling in one place means every tool behaves the same way and an
error is always a clear ValueError message that the tool layer turns into an
{"error": ...} answer. Every result is labelled by finish() with a
result_type: "calculation" (exact rule-based math), "reference" (a verified
figure looked up from our files) or "formula_estimate" (a formula applied to
numbers the user supplied, with stated assumptions), so the agent can say
honestly which kind of answer it is giving.
"""

import json
import math
import os
from pathlib import Path

from dotenv import load_dotenv

from backend.calculator import load_rules

load_dotenv()

PARAMETERS_PATH = Path(__file__).parent.parent / "data" / "tax_parameters_2026.json"

PROVINCE_ALIASES = {
    "newfoundland": "NL",
    "newfoundland and labrador": "NL",
    "pei": "PE",
    "p.e.i.": "PE",
    "prince edward island": "PE",
    "nova scotia": "NS",
    "new brunswick": "NB",
    "quebec": "QC",
    "québec": "QC",
    "ontario": "ON",
    "manitoba": "MB",
    "saskatchewan": "SK",
    "alberta": "AB",
    "british columbia": "BC",
    "yukon": "YT",
    "northwest territories": "NT",
    "nunavut": "NU",
}

CITY_TO_PROVINCE = {
    "toronto": "ON",
    "ottawa": "ON",
    "mississauga": "ON",
    "brampton": "ON",
    "hamilton": "ON",
    "london": "ON",
    "markham": "ON",
    "vaughan": "ON",
    "kitchener": "ON",
    "waterloo": "ON",
    "windsor": "ON",
    "kingston": "ON",
    "oshawa": "ON",
    "barrie": "ON",
    "guelph": "ON",
    "sudbury": "ON",
    "thunder bay": "ON",
    "burlington": "ON",
    "oakville": "ON",
    "niagara falls": "ON",
    "st. catharines": "ON",
    "cambridge": "ON",
    "peterborough": "ON",
    "richmond hill": "ON",
    "montreal": "QC",
    "montréal": "QC",
    "quebec city": "QC",
    "laval": "QC",
    "gatineau": "QC",
    "longueuil": "QC",
    "sherbrooke": "QC",
    "trois-rivières": "QC",
    "trois-rivieres": "QC",
    "saguenay": "QC",
    "lévis": "QC",
    "levis": "QC",
    "vancouver": "BC",
    "victoria": "BC",
    "surrey": "BC",
    "burnaby": "BC",
    "richmond": "BC",
    "kelowna": "BC",
    "abbotsford": "BC",
    "nanaimo": "BC",
    "kamloops": "BC",
    "coquitlam": "BC",
    "langley": "BC",
    "prince george": "BC",
    "port moody": "BC",
    "calgary": "AB",
    "edmonton": "AB",
    "red deer": "AB",
    "lethbridge": "AB",
    "medicine hat": "AB",
    "grande prairie": "AB",
    "airdrie": "AB",
    "st. albert": "AB",
    "fort mcmurray": "AB",
    "saskatoon": "SK",
    "regina": "SK",
    "prince albert": "SK",
    "moose jaw": "SK",
    "winnipeg": "MB",
    "brandon": "MB",
    "halifax": "NS",
    "dartmouth": "NS",
    "sydney": "NS",
    "truro": "NS",
    "moncton": "NB",
    "saint john": "NB",
    "fredericton": "NB",
    "miramichi": "NB",
    "st. john's": "NL",
    "corner brook": "NL",
    "mount pearl": "NL",
    "charlottetown": "PE",
    "summerside": "PE",
    "whitehorse": "YT",
    "dawson city": "YT",
    "yellowknife": "NT",
    "iqaluit": "NU",
}

INCLUDED_IN_RESULTS = [
    "Federal and provincial/territorial bracket tax for the 2026 tax year.",
    "CPP, CPP2 and EI amounts outside Quebec, from verified 2026 figures.",
    "RRSP, TFSA and capital gains figures from verified CRA pages.",
    "The basic personal amount credit (federal and most provinces) in one dedicated tool.",
]

NOT_INCLUDED_IN_RESULTS = [
    "Tax credits other than the basic personal amount (employment amount, CPP/EI, age, "
    "tuition, medical, donations, etc.). Missing dependency: verified amounts for each credit. "
    "The basic personal amount is only available in calculate_tax_after_basic_personal_credit, "
    "and not for Newfoundland and Labrador, Quebec, or Manitoba incomes above 200,000.",
    "Refund or balance-owing estimates. "
    "Missing dependency: tax credits, plus withholding and deduction inputs.",
    "QPP and QPIP (Quebec). Missing dependency: verified Quebec contribution figures.",
    "The Ontario surtax and the Ontario Health Premium.",
    "The Quebec abatement on federal tax, so combined Quebec totals are not final.",
    "Dividends, the dividend tax credit, foreign income and other special income types.",
    "The principal residence exemption and the lifetime capital gains exemption.",
    "Tax years other than 2026. Missing dependency: prior-year rules loaded into the database.",
    "Search of tax guides and CRA documents (RAG). Missing dependency: the "
    "document chunk table, embeddings and the ingestion pipeline are not built yet.",
    "Live checks of web pages. Source checks only compare links with the stored list "
    "and an allowlist of official domains.",
]


def get_rules():
    if os.environ.get("RULES_SOURCE", "json").strip().lower() == "db":
        from backend.rules_db import load_rules_from_db

        return load_rules_from_db()
    return load_rules()


def get_parameters():
    with open(PARAMETERS_PATH) as f:
        return json.load(f)


def check_amount(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number")
    if not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    if value < 0:
        raise ValueError(f"{label} cannot be negative")
    return float(value)


def check_year(value, label, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a whole year such as 2026")
    if not math.isfinite(value) or int(value) != value:
        raise ValueError(f"{label} must be a whole year such as 2026")
    year = int(value)
    if not low <= year <= high:
        raise ValueError(f"{label} must be between {low} and {high}")
    return year


def normalize_province(value, rules):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Province is required")
    jurisdictions = rules["jurisdictions"]
    names = {
        j["name"].lower(): code
        for code, j in jurisdictions.items()
        if code != "federal"
    }
    parts = [p.strip().lower() for p in value.split(",") if p.strip()]
    for part in reversed(parts):
        candidates = [
            part.upper(),
            names.get(part),
            PROVINCE_ALIASES.get(part),
            CITY_TO_PROVINCE.get(part),
        ]
        for code in candidates:
            if code and code != "FEDERAL" and code in jurisdictions:
                return code
    raise ValueError(
        f"Could not identify a province or territory from '{value}'. Use a "
        "two-letter code: NL, PE, NS, NB, QC, ON, MB, SK, AB, BC, YT, NT or NU."
    )


def caveats(code):
    notes = []
    if code == "ON":
        notes.append("Ontario surtax and Ontario Health Premium are not included.")
    if code == "QC":
        notes.append(
            "Quebec's abatement on federal tax is not applied, so the combined "
            "Quebec total is not reliable as a final number."
        )
    return notes


def finish(data, kind, tax_year):
    return {"result_type": kind, "tax_year": tax_year, **data}
