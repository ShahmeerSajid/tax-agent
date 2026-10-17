
import os

import psycopg
from dotenv import load_dotenv

load_dotenv()

SCHEMA = """
CREATE TABLE IF NOT EXISTS jurisdictions (
    code        TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    source_url  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS brackets (
    id                SERIAL PRIMARY KEY,
    jurisdiction_code TEXT NOT NULL REFERENCES jurisdictions(code),
    tax_year          INT NOT NULL,
    position          INT NOT NULL,
    up_to             NUMERIC(14, 2),
    rate              NUMERIC(7, 5) NOT NULL,
    UNIQUE (jurisdiction_code, tax_year, position)
);
"""

if __name__ == "__main__":
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute(SCHEMA)
    print("Tables ready")