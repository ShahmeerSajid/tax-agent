"""
This file applies the basic personal amount (BPA) credit, the one credit that
nearly every taxpayer gets. The BPA is an amount of income that is treated as
tax-free. In practice it becomes a non-refundable credit: the BPA multiplied by
the lowest bracket rate is subtracted from the bracket tax, and the result
cannot go below zero. The federal BPA starts at its maximum and shrinks
linearly to its minimum for net incomes between two thresholds. The provincial
BPA amounts, the Yukon rule (it follows the federal formula) and the Manitoba
high-income rule are read from data/tax_credits_2026.json, which stores the
official source page for each figure. The bracket tax itself still comes from
the same calculator used everywhere else.

We need this because bracket tax alone overstates what most people owe by
roughly the BPA credit, and the AI must never subtract credits itself. We only
apply credits we have verified. For Newfoundland and Labrador, for Quebec and
for Manitoba incomes above the stored limit, the provincial credit is NOT
applied, and the result says so with incomplete set to true instead of
guessing. Other credits (employment amount, CPP and EI credits, age, tuition,
medical, donations and so on), the Ontario surtax and Health Premium, and the
Quebec abatement are still not included, and the result lists them.
"""

import json
from pathlib import Path

from backend.calculator import calculate_tax
from backend.common import caveats, check_amount, finish, get_rules, normalize_province

CREDITS_PATH = Path(__file__).parent.parent / "data" / "tax_credits_2026.json"

OTHER_CREDITS_NOTE = (
    "Only the basic personal amount credit is applied. Other credits (Canada employment "
    "amount, CPP/EI credits, age, tuition, medical, donations, etc.) are not included."
)


def load_credits(path=CREDITS_PATH):
    with open(path) as f:
        return json.load(f)


def federal_bpa(net_income, federal):
    low, high = federal["phase_start_net_income"], federal["phase_end_net_income"]
    top, bottom = federal["bpa_max"], federal["bpa_min"]
    if net_income <= low:
        return float(top)
    if net_income >= high:
        return float(bottom)
    return round(top - (net_income - low) * (top - bottom) / (high - low), 2)


def _provincial_bpa(income, code, credits, federal_amount):
    entry = credits["provinces"].get(code)
    if entry is None:
        return None, credits["not_available"].get(code, "No verified BPA is stored.")
    if entry.get("follows_federal_formula"):
        return federal_amount, None
    if "applied_up_to_net_income" in entry and income > entry["applied_up_to_net_income"]:
        return None, (
            f"The {code} BPA is reduced for net income above "
            f"{entry['applied_up_to_net_income']:,}; that reduction is not modelled."
        )
    return float(entry["bpa"]), None


def tax_after_basic_personal_credit(income, province):
    rules = get_rules()
    credits = load_credits()
    amount = check_amount(income, "Income")
    code = normalize_province(province, rules)
    tax = calculate_tax(amount, code, rules)

    fed_rate = rules["jurisdictions"]["federal"]["brackets"][0]["rate"]
    prov_rate = rules["jurisdictions"][code]["brackets"][0]["rate"]
    fed_bpa = federal_bpa(amount, credits["federal"])
    fed_credit = round(fed_bpa * fed_rate, 2)
    fed_net = round(max(tax["federal_tax"] - fed_credit, 0.0), 2)

    prov_bpa, reason = _provincial_bpa(amount, code, credits, fed_bpa)
    missing = []
    if prov_bpa is None:
        prov_credit = 0.0
        prov_net = tax["provincial_tax"]
        missing.append(f"Provincial BPA credit not applied: {reason}")
    else:
        prov_credit = round(prov_bpa * prov_rate, 2)
        prov_net = round(max(tax["provincial_tax"] - prov_credit, 0.0), 2)

    sources = tax["sources"] + credits["federal"]["source_urls"]
    prov_entry = credits["provinces"].get(code)
    if prov_entry:
        sources.append(prov_entry["source_url"])

    return finish(
        {
            "income": amount,
            "province": code,
            "federal_tax_before_credit": tax["federal_tax"],
            "federal_bpa": fed_bpa,
            "federal_bpa_credit": fed_credit,
            "federal_tax_after_credit": fed_net,
            "provincial_tax_before_credit": tax["provincial_tax"],
            "provincial_bpa": prov_bpa,
            "provincial_bpa_credit": prov_credit,
            "provincial_tax_after_credit": prov_net,
            "total_tax_before_credit": tax["total_tax"],
            "total_tax_after_basic_personal_credit": round(fed_net + prov_net, 2),
            "incomplete": bool(missing),
            "missing": missing,
            "caveats": caveats(code),
            "notes": [OTHER_CREDITS_NOTE, credits["note"]],
            "sources": sources,
        },
        "calculation",
        rules["tax_year"],
    )
