"""
This file calculates payroll contributions and self-employment amounts from the
verified 2026 figures stored in data/tax_parameters_2026.json. For an employee
outside Quebec it computes the CPP contribution (rate applied to earnings
between the basic exemption and the year's maximum pensionable earnings), the
second additional CPP contribution (CPP2, on earnings between the two ceilings)
and the EI premium (rate applied up to the maximum insurable earnings), each
capped at the official maximum, plus the employer's matching side. For a
self-employed person it works out net business income (revenue minus expenses),
the bracket tax on it, and the self-employed CPP and CPP2 amounts.

We need this because contribution rates, ceilings and maximums change every
year and an AI model must never recall them from memory. Quebec residents pay
into the QPP and QPIP instead of the CPP and have a different EI rate. We only
have verified figures for the Quebec EI rate, so for Quebec the tools return
the EI amount and clearly list QPP and QPIP as missing, rather than guessing.
Results assume a full year, one employer, age 18 to 69 and no exemptions, and
they say so. They are labelled "calculation" for the formulas and
"formula_estimate" where the assumptions matter.
"""

from backend.calculator import calculate_tax
from backend.common import caveats, check_amount, finish, get_parameters, get_rules, normalize_province

ASSUMPTIONS = [
    "Assumes a full calendar year with one employer, age 18 to 69, and no contribution exemptions.",
    "Income tax credits for these contributions are not applied.",
]
QUEBEC_MISSING = [
    "QPP and QPIP amounts are not included: verified Quebec contribution figures are not in the project yet."
]


def _cpp_employee(earnings, cpp):
    pensionable = max(min(earnings, cpp["ympe"]) - cpp["basic_exemption"], 0.0)
    base = min(round(pensionable * cpp["employee_rate"], 2), cpp["employee_max"])
    above = max(min(earnings, cpp["yampe"]) - cpp["ympe"], 0.0)
    cpp2 = min(round(above * cpp["cpp2_employee_rate"], 2), cpp["cpp2_employee_max"])
    return base, cpp2


def _cpp_self_employed(earnings, cpp):
    pensionable = max(min(earnings, cpp["ympe"]) - cpp["basic_exemption"], 0.0)
    base = min(round(pensionable * cpp["self_employed_rate"], 2), cpp["self_employed_max"])
    above = max(min(earnings, cpp["yampe"]) - cpp["ympe"], 0.0)
    cpp2 = min(round(above * cpp["cpp2_self_employed_rate"], 2), cpp["cpp2_self_employed_max"])
    return base, cpp2


def employee_payroll_deductions(annual_employment_income, province):
    rules = get_rules()
    params = get_parameters()
    cpp, ei = params["cpp"], params["ei"]
    earnings = check_amount(annual_employment_income, "Employment income")
    code = normalize_province(province, rules)
    in_quebec = code == "QC"

    rate = ei["rate_quebec"] if in_quebec else ei["rate_outside_quebec"]
    cap = ei["max_premium_quebec"] if in_quebec else ei["max_premium_outside_quebec"]
    ei_premium = min(round(min(earnings, ei["max_insurable_earnings"]) * rate, 2), cap)
    employer_ei = round(ei_premium * ei["employer_multiplier"], 2)

    if in_quebec:
        cpp_base = cpp2 = None
        employee_total = ei_premium
        employer = {"ei": employer_ei}
        missing = QUEBEC_MISSING
    else:
        cpp_base, cpp2 = _cpp_employee(earnings, cpp)
        employee_total = round(cpp_base + cpp2 + ei_premium, 2)
        employer = {"cpp": cpp_base, "cpp2": cpp2, "ei": employer_ei}
        missing = []

    return finish(
        {
            "annual_employment_income": earnings,
            "province": code,
            "employee": {
                "cpp": cpp_base,
                "cpp2": cpp2,
                "ei": ei_premium,
                "total_listed": employee_total,
            },
            "employer_matching": employer,
            "incomplete": bool(missing),
            "missing": missing,
            "notes": ASSUMPTIONS,
            "sources": cpp["source_urls"] + ei["source_urls"],
        },
        "formula_estimate",
        rules["tax_year"],
    )


def self_employment_tax(gross_revenue, business_expenses, province):
    rules = get_rules()
    params = get_parameters()
    cpp = params["cpp"]
    revenue = check_amount(gross_revenue, "Gross revenue")
    expenses = check_amount(business_expenses, "Business expenses")
    code = normalize_province(province, rules)

    net = round(revenue - expenses, 2)
    taxable = max(net, 0.0)
    tax = calculate_tax(taxable, code, rules)
    notes = [
        "Net business income is revenue minus expenses; which expenses are deductible is not checked here.",
        "The CPP deduction and credit for self-employed people, GST/HST and tax instalments are not modelled.",
        "Self-employed people do not pay EI premiums unless they have opted in; EI is not included.",
        "Income tax is on business income only, with no other income and no credits.",
    ]
    if net < 0:
        notes.append("Expenses are larger than revenue, so there is a business loss and no tax is calculated on it.")

    if code == "QC":
        cpp_base = cpp2 = None
        missing = QUEBEC_MISSING
    else:
        cpp_base, cpp2 = _cpp_self_employed(taxable, cpp)
        missing = []

    return finish(
        {
            "gross_revenue": revenue,
            "business_expenses": expenses,
            "net_business_income": net,
            "province": code,
            "federal_tax": tax["federal_tax"],
            "provincial_tax": tax["provincial_tax"],
            "income_tax_before_credits": tax["total_tax"],
            "self_employed_cpp": cpp_base,
            "self_employed_cpp2": cpp2,
            "total_listed": round(tax["total_tax"] + (cpp_base or 0.0) + (cpp2 or 0.0), 2),
            "incomplete": bool(missing),
            "missing": missing,
            "caveats": caveats(code),
            "notes": notes,
            "sources": tax["sources"] + cpp["source_urls"],
        },
        "formula_estimate",
        rules["tax_year"],
    )
