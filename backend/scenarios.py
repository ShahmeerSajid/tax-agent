"""
This file runs several "what if" scenarios side by side and compares each one
with a base case. A scenario is a label plus an income change (for example a
raise or a lost job, positive or negative) and an optional deduction (such as
an RRSP contribution). For every scenario the function works out the taxable
income, runs the same federal plus provincial bracket calculation as every other
tool, and reports the total tax and how much more or less tax it is than the
base case.

We need this because people rarely ask one question: they ask "what if I get a
raise and also contribute to my RRSP" or "what if I earn less next year", and
doing the comparison in one tool call keeps the numbers consistent and stops
the AI from doing any subtraction itself. The Scenario class describes each
scenario to Gemini through LangChain with typed fields, and the function
limits the number of scenarios so a request cannot run away. Results are bracket
tax before credits and are labelled "calculation".
"""

from pydantic import BaseModel, Field

from backend.calculator import calculate_tax
from backend.common import caveats, check_amount, finish, get_rules, normalize_province

MAX_SCENARIOS = 10


class Scenario(BaseModel):
    label: str = Field(description="Short name for the scenario, for example 'Raise of 10,000'.")
    income_change: float = Field(
        default=0.0,
        description="Change to the base income in dollars. Positive for a raise, negative for a cut.",
    )
    deduction: float = Field(
        default=0.0,
        description="Deduction in dollars, such as an RRSP contribution. Zero or more.",
    )


def simulate_scenarios(province, base_income, scenarios):
    rules = get_rules()
    base = check_amount(base_income, "Base income")
    code = normalize_province(province, rules)
    if not scenarios:
        raise ValueError("Provide at least one scenario")
    if len(scenarios) > MAX_SCENARIOS:
        raise ValueError(f"At most {MAX_SCENARIOS} scenarios are allowed")

    base_tax = calculate_tax(base, code, rules)["total_tax"]
    rows = []
    for item in scenarios:
        scenario = item if isinstance(item, Scenario) else Scenario(**item)
        deduction = check_amount(scenario.deduction, f"Deduction in '{scenario.label}'")
        gross = base + scenario.income_change
        if gross < 0:
            raise ValueError(f"Scenario '{scenario.label}' gives a negative income")
        if deduction > gross:
            raise ValueError(f"Scenario '{scenario.label}' has a deduction larger than income")
        taxable = round(gross - deduction, 2)
        result = calculate_tax(taxable, code, rules)
        rows.append(
            {
                "label": scenario.label,
                "income": round(gross, 2),
                "deduction": deduction,
                "taxable_income": taxable,
                "federal_tax": result["federal_tax"],
                "provincial_tax": result["provincial_tax"],
                "total_tax": result["total_tax"],
                "tax_change_vs_base": round(result["total_tax"] - base_tax, 2),
                "average_rate": round(result["total_tax"] / taxable, 4) if taxable > 0 else 0.0,
            }
        )
    return finish(
        {
            "province": code,
            "base_income": base,
            "base_total_tax": base_tax,
            "scenarios": rows,
            "caveats": caveats(code),
            "sources": [
                rules["jurisdictions"]["federal"]["source_url"],
                rules["jurisdictions"][code]["source_url"],
            ],
        },
        "calculation",
        rules["tax_year"],
    )
