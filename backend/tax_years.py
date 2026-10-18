"""
This file lets the agent compare tax between different tax years. It reads
from the Neon database, because the database is the only place that can hold
the brackets of more than one year: list_available_years() asks which tax years
have brackets stored, and compare_years() loads the rules of two years with
the existing rules_db.load_rules_from_db(year), runs the normal calculator on
each, and reports the difference in tax at the same income.

We need this because "how did my tax change compared with last year" is a
common question, but today the database holds only the 2026 brackets, so any
comparison will honestly return an error that names the missing year instead
of making something up. To make the tool useful you will later need to add the
rules of earlier years to the database (a data file for each year and a loader
that accepts it, since load_data.py currently loads only the 2026 file). Until
then the tool also tells the agent which years are available. It needs
DATABASE_URL in .env and does not use the JSON file.
"""

import os

import psycopg

from backend.calculator import calculate_tax
from backend.common import caveats, check_amount, check_year, finish, get_rules, normalize_province
from backend.rules_db import load_rules_from_db




def available_years():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL is not set, so stored tax years cannot be listed")
    try:
        with psycopg.connect(url) as conn:
            rows = conn.execute("SELECT DISTINCT tax_year FROM brackets ORDER BY tax_year").fetchall()
    except psycopg.Error:
        raise ValueError("Could not read the stored tax years from the database")
    years = [r[0] for r in rows]
    return finish({"available_years": years}, "reference", get_rules()["tax_year"])




def compare_years(income, province, year_a, year_b):
    amount = check_amount(income, "Income")
    first = check_year(year_a, "First year", 1990, 2100)
    second = check_year(year_b, "Second year", 1990, 2100)
    code = normalize_province(province, get_rules())
    if not os.environ.get("DATABASE_URL"):
        raise ValueError("DATABASE_URL is not set, so stored tax years cannot be compared")

    results = {}
    for year in (first, second):
        try:
            rules = load_rules_from_db(year)
        except (psycopg.Error, KeyError):
            raise ValueError("Could not read tax rules from the database")
        if "federal" not in rules["jurisdictions"] or code not in rules["jurisdictions"]:
            stored = available_years()["available_years"]
            raise ValueError(
                f"No stored rules for {code} in tax year {year}. Stored tax years: {stored}. "
                "Earlier years must be added to the database before they can be compared."
            )
        results[year] = calculate_tax(amount, code, rules)

    a, b = results[first], results[second]
    return finish(
        {
            "income": amount,
            "province": code,
            "year_a": {"year": first, "total_tax": a["total_tax"], "federal_tax": a["federal_tax"], "provincial_tax": a["provincial_tax"]},
            "year_b": {"year": second, "total_tax": b["total_tax"], "federal_tax": b["federal_tax"], "provincial_tax": b["provincial_tax"]},
            "difference_b_minus_a": round(b["total_tax"] - a["total_tax"], 2),
            "caveats": caveats(code)
            + ["Same income in both years; bracket tax before credits, using each year's stored brackets."],
            "sources": sorted(set(a["sources"] + b["sources"])),
        },
        "calculation",
        second,
    )
