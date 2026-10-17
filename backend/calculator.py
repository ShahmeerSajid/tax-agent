

# What the calculator does: it takes an income and a province, and works out the tax. 
# For each bracket, it taxes the slice of income inside that bracket at its rate, adds up the slices, and
# does this for federal and provincial. It returns the totals plus the source links.

# What it needs: the list of brackets for each jurisdiction. It doesn’t store them, so 
# it has to be given them.

# Where rules_db.py helps and how does it help the calculator.py:
# Neon database ──► rules_db.py ──► calculator

# The rules_db.py file reads the tax rules back out of the Neon database and returns them
# in exactly the same shape as the JSON file. calculator.py needs rules_db.py

# Example:
# rules = load_rules_from_db()
# calculate_tax(85000, "ON", rules)






import json
from pathlib import Path

RULES_PATH = Path(__file__).parent.parent / "data" / "tax_rules_2026.json"




def load_rules(path=RULES_PATH):
    with open(path) as f:
        return json.load(f)







def bracket_tax(income, brackets):
    tax = 0.0
    lower = 0.0
    for b in brackets:
        upper = b["up_to"]
        top = income if upper is None else min(income, upper)
        if top > lower:
            tax += (top - lower) * b["rate"]
        if upper is None or income <= upper:
            break
        lower = upper
    return round(tax, 2)








def calculate_tax(income, province, rules):
    jurisdictions = rules["jurisdictions"]
    if province == "federal" or province not in jurisdictions:
        raise ValueError(f"Unknown province: {province}")
    if income < 0:
        raise ValueError("Income cannot be negative")

    federal = bracket_tax(income, jurisdictions["federal"]["brackets"])
    provincial = bracket_tax(income, jurisdictions[province]["brackets"])
    return {
        "income": income,
        "province": province,
        "federal_tax": federal,
        "provincial_tax": provincial,
        "total_tax": round(federal + provincial, 2),
        "sources": [
            jurisdictions["federal"]["source_url"],
            jurisdictions[province]["source_url"],
        ],
    }
    
    
    
