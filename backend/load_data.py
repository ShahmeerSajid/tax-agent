
"""
The code copies the tax rules from our JSON file (data/tax_rules_2026.json)
into the Neon database. It reads every jurisdiction (federal plus each
province and territory) and saves its name, its source link, and each of its
tax brackets as rows in the jurisdictions and brackets tables that we created
earlier. Before inserting, it deletes the brackets already stored for that tax
year, so running the script again never creates duplicates, and any edit you
make to the JSON file is simply re-synced into the database.

We need this because the database is where the rest of the project will read
its rules from: the calculator, the AI assistant and, later, the ingestion
agent that proposes updates. Keeping the data in a database, instead of only in
a file, lets us store sources and change history, search it with SQL, and use
the same rules from the website, the scrapers and the agents. Run it with:
python -m backend.load_data
"""



import json
import os

import psycopg
from dotenv import load_dotenv

from backend.calculator import RULES_PATH

load_dotenv()


def load():
    with open(RULES_PATH) as f:
        rules = json.load(f)
    year = rules["tax_year"]

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute("DELETE FROM brackets WHERE tax_year = %s", (year,))
        for code, j in rules["jurisdictions"].items():
            conn.execute(
                """
                INSERT INTO jurisdictions (code, name, source_url)
                VALUES (%s, %s, %s)
                ON CONFLICT (code) DO UPDATE
                SET name = EXCLUDED.name, source_url = EXCLUDED.source_url
                """,
                (code, j["name"], j["source_url"]),
            )
            for position, b in enumerate(j["brackets"]):
                conn.execute(
                    """
                    INSERT INTO brackets
                        (jurisdiction_code, tax_year, position, up_to, rate)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (code, year, position, b["up_to"], b["rate"]),
                )
    print(f"Loaded {len(rules['jurisdictions'])} jurisdictions for {year}")


if __name__ == "__main__":
    load()