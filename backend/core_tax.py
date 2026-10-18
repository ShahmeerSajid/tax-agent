"""
This file contains the core bracket-tax logic behind the agent's basic tools:
looking up brackets, calculating federal plus provincial tax, showing the
bracket-by-bracket breakdown, average and marginal rates, deduction and raise
what-ifs, after-tax income and its reverse, distance to the next bracket,
deduction needed to drop a bracket, province comparison and pay-period
conversion. Every function takes plain values, validates them, uses the
calculator in backend/calculator.py for all tax math, and returns a plain
dictionary, so the same logic can be used by tools, tests, scripts or the API.

We keep it separate from tools.py because tools.py should only describe each
tool to the AI model and call into logic like this. Splitting them means the
business logic can be tested without LangChain or Gemini, and several tools
can share one function. All results here are 2026 bracket tax before credits,
so they are labelled with result_type "calculation" and carry caveats where a
known rule (the Ontario surtax, the Quebec abatement) is not modelled.
"""

from backend.calculator import bracket_tax, calculate_tax
from backend.common import (
    INCLUDED_IN_RESULTS,
    NOT_INCLUDED_IN_RESULTS,
    caveats,
    check_amount,
    finish,
    get_rules,
    normalize_province,
)

PERIODS_PER_YEAR = {
    "annual": 1,
    "yearly": 1,
    "year": 1,
    "monthly": 12,
    "month": 12,
    "semi-monthly": 24,
    "semimonthly": 24,
    "biweekly": 26,
    "bi-weekly": 26,
    "weekly": 52,
    "week": 52,
}


def _marginal(income, brackets):
    lower = 0.0
    for b in brackets:
        upper = b["up_to"]
        if upper is None or income < upper:
            return {"rate": b["rate"], "bracket_from": lower, "bracket_to": upper}
        lower = upper
    return {"rate": brackets[-1]["rate"], "bracket_from": lower, "bracket_to": None}


def _bracket_rows(income, brackets, only_reached):
    rows = []
    lower = 0.0
    for b in brackets:
        upper = b["up_to"]
        top = income if upper is None else min(income, upper)
        taxed = max(top - lower, 0.0)
        if taxed > 0 or not only_reached:
            rows.append(
                {
                    "from": lower,
                    "to": upper,
                    "rate": b["rate"],
                    "rate_percent": round(b["rate"] * 100, 3),
                    "income_in_bracket": round(taxed, 2),
                    "tax": round(taxed * b["rate"], 2),
                }
            )
        if upper is None:
            break
        lower = upper
    return rows


def _next_threshold(income, brackets):
    for i, b in enumerate(brackets):
        upper = b["up_to"]
        if upper is None:
            return None
        if income < upper:
            return {
                "threshold": upper,
                "dollars_to_go": round(upper - income, 2),
                "rate_now": b["rate"],
                "rate_after": brackets[i + 1]["rate"],
            }
    return None


def _drop_info(income, brackets):
    for i, b in enumerate(brackets):
        upper = b["up_to"]
        if upper is None or income < upper:
            if i == 0:
                return None
            edge = brackets[i - 1]["up_to"]
            return {
                "current_rate": b["rate"],
                "rate_after": brackets[i - 1]["rate"],
                "bracket_starts_at": edge,
                "income_taxed_at_current_rate": round(income - edge, 2),
            }
    return None


def _after_tax(income, code, rules):
    return income - calculate_tax(income, code, rules)["total_tax"]


def list_jurisdictions():
    rules = get_rules()
    return finish(
        {
            "jurisdictions": [
                {"code": code, "name": j["name"], "source_url": j["source_url"]}
                for code, j in rules["jurisdictions"].items()
            ]
        },
        "reference",
        rules["tax_year"],
    )


def resolve_province(location):
    rules = get_rules()
    code = normalize_province(location, rules)
    return finish(
        {
            "input": location,
            "province": code,
            "name": rules["jurisdictions"][code]["name"],
        },
        "reference",
        rules["tax_year"],
    )


def get_tax_brackets(jurisdiction):
    rules = get_rules()
    key = jurisdiction.strip().lower() if isinstance(jurisdiction, str) else ""
    code = "federal" if key == "federal" else normalize_province(jurisdiction, rules)
    j = rules["jurisdictions"][code]
    rows = _bracket_rows(0.0, j["brackets"], only_reached=False)
    return finish(
        {
            "jurisdiction": code,
            "name": j["name"],
            "brackets": [
                {k: row[k] for k in ("from", "to", "rate", "rate_percent")}
                for row in rows
            ],
            "caveats": caveats(code),
            "sources": [j["source_url"]],
        },
        "reference",
        rules["tax_year"],
    )


def calculator_limitations():
    rules = get_rules()
    return finish(
        {
            "included": INCLUDED_IN_RESULTS,
            "not_included_or_not_available": NOT_INCLUDED_IN_RESULTS,
        },
        "reference",
        rules["tax_year"],
    )


def income_tax(income, province):
    rules = get_rules()
    amount = check_amount(income, "Income")
    code = normalize_province(province, rules)
    result = calculate_tax(amount, code, rules)
    result["average_rate"] = round(result["total_tax"] / amount, 4) if amount > 0 else 0.0
    result["caveats"] = caveats(code)
    return finish(result, "calculation", rules["tax_year"])


def breakdown(income, province):
    rules = get_rules()
    amount = check_amount(income, "Income")
    code = normalize_province(province, rules)
    federal = rules["jurisdictions"]["federal"]
    provincial = rules["jurisdictions"][code]
    return finish(
        {
            "income": amount,
            "province": code,
            "federal": {
                "brackets": _bracket_rows(amount, federal["brackets"], True),
                "tax": bracket_tax(amount, federal["brackets"]),
            },
            "provincial": {
                "brackets": _bracket_rows(amount, provincial["brackets"], True),
                "tax": bracket_tax(amount, provincial["brackets"]),
            },
            "total_tax": calculate_tax(amount, code, rules)["total_tax"],
            "caveats": caveats(code),
            "sources": [federal["source_url"], provincial["source_url"]],
        },
        "calculation",
        rules["tax_year"],
    )


def tax_rates(income, province):
    rules = get_rules()
    amount = check_amount(income, "Income")
    code = normalize_province(province, rules)
    federal = rules["jurisdictions"]["federal"]
    provincial = rules["jurisdictions"][code]
    total = calculate_tax(amount, code, rules)["total_tax"]
    fed = _marginal(amount, federal["brackets"])
    prov = _marginal(amount, provincial["brackets"])
    return finish(
        {
            "income": amount,
            "province": code,
            "average_rate": round(total / amount, 4) if amount > 0 else 0.0,
            "federal_marginal_rate": fed["rate"],
            "provincial_marginal_rate": prov["rate"],
            "combined_marginal_rate": round(fed["rate"] + prov["rate"], 5),
            "federal_bracket": fed,
            "provincial_bracket": prov,
            "caveats": caveats(code),
            "sources": [federal["source_url"], provincial["source_url"]],
        },
        "calculation",
        rules["tax_year"],
    )


def deduction_comparison(income, province, deduction):
    rules = get_rules()
    amount = check_amount(income, "Income")
    reduction = check_amount(deduction, "Deduction")
    if reduction > amount:
        raise ValueError("Deduction cannot be larger than income")
    code = normalize_province(province, rules)
    without = calculate_tax(amount, code, rules)
    with_deduction = calculate_tax(amount - reduction, code, rules)
    return finish(
        {
            "income": amount,
            "deduction": reduction,
            "province": code,
            "tax_without_deduction": without["total_tax"],
            "tax_with_deduction": with_deduction["total_tax"],
            "tax_saved": round(without["total_tax"] - with_deduction["total_tax"], 2),
            "caveats": caveats(code),
            "sources": without["sources"],
        },
        "calculation",
        rules["tax_year"],
    )


def additional_income(income, province, extra_income):
    rules = get_rules()
    amount = check_amount(income, "Income")
    extra = check_amount(extra_income, "Additional income")
    code = normalize_province(province, rules)
    before = calculate_tax(amount, code, rules)
    after = calculate_tax(amount + extra, code, rules)
    extra_tax = round(after["total_tax"] - before["total_tax"], 2)
    return finish(
        {
            "income": amount,
            "additional_income": extra,
            "province": code,
            "tax_before": before["total_tax"],
            "tax_after": after["total_tax"],
            "extra_tax": extra_tax,
            "amount_kept": round(extra - extra_tax, 2),
            "tax_rate_on_additional_income": round(extra_tax / extra, 4) if extra > 0 else 0.0,
            "caveats": caveats(code),
            "sources": before["sources"],
        },
        "calculation",
        rules["tax_year"],
    )


def after_tax_income(income, province):
    rules = get_rules()
    amount = check_amount(income, "Income")
    code = normalize_province(province, rules)
    result = calculate_tax(amount, code, rules)
    net = round(amount - result["total_tax"], 2)
    return finish(
        {
            "income": amount,
            "province": code,
            "total_tax": result["total_tax"],
            "after_tax_income_yearly": net,
            "after_tax_income_monthly": round(net / 12, 2),
            "after_tax_income_biweekly": round(net / 26, 2),
            "caveats": caveats(code)
            + ["Credits, CPP and EI are not applied, so this is not real take-home pay."],
            "sources": result["sources"],
        },
        "formula_estimate",
        rules["tax_year"],
    )


def income_needed(target_after_tax_income, province):
    import math

    rules = get_rules()
    target = check_amount(target_after_tax_income, "Target")
    code = normalize_province(province, rules)
    if target == 0:
        needed = 0.0
    else:
        low, high = target, target * 2
        for _ in range(60):
            if _after_tax(high, code, rules) >= target:
                break
            high *= 2
        else:
            raise ValueError("Target is too large to compute")
        for _ in range(80):
            mid = (low + high) / 2
            if _after_tax(mid, code, rules) < target:
                low = mid
            else:
                high = mid
        needed = math.ceil(high * 100) / 100
    result = calculate_tax(needed, code, rules)
    return finish(
        {
            "target_after_tax_income": target,
            "province": code,
            "income_needed": needed,
            "total_tax": result["total_tax"],
            "after_tax_income": round(needed - result["total_tax"], 2),
            "caveats": caveats(code)
            + ["Credits, CPP and EI are not applied, so this is not real take-home pay."],
            "sources": result["sources"],
        },
        "formula_estimate",
        rules["tax_year"],
    )


def next_threshold(income, province):
    rules = get_rules()
    amount = check_amount(income, "Income")
    code = normalize_province(province, rules)
    federal = rules["jurisdictions"]["federal"]
    provincial = rules["jurisdictions"][code]
    return finish(
        {
            "income": amount,
            "province": code,
            "federal_next_bracket": _next_threshold(amount, federal["brackets"]),
            "provincial_next_bracket": _next_threshold(amount, provincial["brackets"]),
            "caveats": caveats(code),
            "sources": [federal["source_url"], provincial["source_url"]],
        },
        "calculation",
        rules["tax_year"],
    )


def deduction_to_drop_bracket(income, province):
    rules = get_rules()
    amount = check_amount(income, "Income")
    code = normalize_province(province, rules)
    federal = rules["jurisdictions"]["federal"]
    provincial = rules["jurisdictions"][code]
    return finish(
        {
            "income": amount,
            "province": code,
            "federal_drop": _drop_info(amount, federal["brackets"]),
            "provincial_drop": _drop_info(amount, provincial["brackets"]),
            "caveats": caveats(code),
            "sources": [federal["source_url"], provincial["source_url"]],
        },
        "calculation",
        rules["tax_year"],
    )


def compare_provinces(income, provinces):
    rules = get_rules()
    amount = check_amount(income, "Income")
    if provinces:
        codes = []
        for item in provinces:
            code = normalize_province(item, rules)
            if code not in codes:
                codes.append(code)
    else:
        codes = [c for c in rules["jurisdictions"] if c != "federal"]
    rows = []
    for code in codes:
        result = calculate_tax(amount, code, rules)
        rows.append(
            {
                "province": code,
                "name": rules["jurisdictions"][code]["name"],
                "federal_tax": result["federal_tax"],
                "provincial_tax": result["provincial_tax"],
                "total_tax": result["total_tax"],
                "average_rate": round(result["total_tax"] / amount, 4) if amount > 0 else 0.0,
            }
        )
    rows.sort(key=lambda r: r["total_tax"])
    lowest = rows[0]["total_tax"]
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
        row["more_than_lowest"] = round(row["total_tax"] - lowest, 2)
    notes = ["Bracket tax only, before credits."]
    for code in codes:
        notes.extend(caveats(code))
    return finish(
        {
            "income": amount,
            "results": rows,
            "caveats": notes,
            "sources": [rules["jurisdictions"]["federal"]["source_url"]]
            + [rules["jurisdictions"][c]["source_url"] for c in codes],
        },
        "calculation",
        rules["tax_year"],
    )


def annualize(amount, period, hours_per_week, weeks_per_year):
    value = check_amount(amount, "Amount")
    key = period.strip().lower() if isinstance(period, str) else ""
    if key in {"hourly", "hour"}:
        hours = check_amount(hours_per_week, "Hours per week")
        weeks = check_amount(weeks_per_year, "Weeks per year")
        if not 0 < hours <= 168:
            raise ValueError("Hours per week must be between 0 and 168")
        if not 0 < weeks <= 52:
            raise ValueError("Weeks per year must be between 0 and 52")
        annual = value * hours * weeks
        how = f"{value} x {hours} hours x {weeks} weeks"
    elif key in PERIODS_PER_YEAR:
        count = PERIODS_PER_YEAR[key]
        annual = value * count
        how = f"{value} x {count} pay periods"
    else:
        raise ValueError(
            "Period must be one of: hourly, weekly, biweekly, semi-monthly, monthly, annual"
        )
    return {"result_type": "calculation", "annual_income": round(annual, 2), "calculation": how}
