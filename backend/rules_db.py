
"""
This file reads the tax rules back out of the Neon database and returns them
in exactly the same shape as the JSON file (a dictionary with the tax year and
one entry per jurisdiction, each holding its name, source link and list of
brackets). It picks the newest tax year by default, skips any jurisdiction that
has no brackets for that year, and converts the database's exact decimal
numbers into normal Python numbers so the calculator can use them directly.

We need it because the database is now the single source of truth for the
rules. Since the output has the same shape as the JSON, the calculator does not
change at all: we simply pass it load_rules_from_db().

Later, when the ingestion agent proposes new rules and I approve them, the
assistant will automatically use the updated numbers without anyone editing a
file or redeploying the code.


This code returns a Python dictionary, not a JSON file or text. It has the same structure as 
the JSON file, but it’s a live object in memory.
e.g.,

{
  "tax_year": 2026,
  "jurisdictions": {
    "federal": {"name": "Federal", "source_url": "...", "brackets": [...]},
    "ON": {"name": "Ontario", "source_url": "...", "brackets": [...]},
    "QC": {...}
  }
}


Then, 

rules = load_rules_from_db()
calculate_tax(85000, "ON", rules)

"""


import os

import psycopg
from dotenv import load_dotenv

load_dotenv()


def load_rules_from_db(year=None):
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        if year is None:
            year = conn.execute("SELECT MAX(tax_year) FROM brackets").fetchone()[0]
        if year is None:
            raise ValueError("No tax rules found in the database")

        jurisdictions = {}
        rows = conn.execute(
            "SELECT code, name, source_url FROM jurisdictions ORDER BY code"
        ).fetchall()
        for code, name, source_url in rows:
            jurisdictions[code] = {
                "name": name,
                "source_url": source_url,
                "brackets": [],
            }

        rows = conn.execute(
            """
            SELECT jurisdiction_code, up_to, rate
            FROM brackets
            WHERE tax_year = %s
            ORDER BY jurisdiction_code, position
            """,
            (year,),
        ).fetchall()
        for code, up_to, rate in rows:
            jurisdictions[code]["brackets"].append(
                {
                    "up_to": None if up_to is None else float(up_to),
                    "rate": float(rate),
                }
            )

    jurisdictions = {c: j for c, j in jurisdictions.items() if j["brackets"]}
    return {"tax_year": year, "jurisdictions": jurisdictions}