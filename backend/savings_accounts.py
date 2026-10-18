"""
This file holds the logic for registered savings accounts: RRSP and TFSA. For
the RRSP it works out a deduction limit using the formula the CRA publishes
(the unused room carried forward, plus the lesser of 18% of last year's earned
income and the annual dollar limit, minus the pension adjustment and net past
service pension adjustment, plus any pension adjustment reversal), and it
works out how much income tax a contribution saves by reusing the same bracket
calculator as every other tool. For the TFSA it adds up the official annual
limits from the first year a person was eligible, then subtracts the
contributions made and adds back earlier withdrawals.

We need this because room and limits are exactly the kind of numbers an AI
would otherwise guess. The dollar limits and the 18% rate come from
data/tax_parameters_2026.json, which stores only figures read from official
CRA pages, and the person's own figures (earned income, pension adjustment,
contributions, withdrawals) must be supplied by them, usually from the
Notice of Assessment or CRA My Account. Because these results depend on
numbers the user types in, they are labelled "formula_estimate", not a
final CRA figure, and the official room shown by the CRA always wins.
"""

from backend.common import check_amount, check_year, finish, get_parameters, get_rules
from backend.core_tax import deduction_comparison


def rrsp_deduction_limit(
    prior_year_earned_income,
    limit_year,
    unused_room_carried_forward,
    pension_adjustment,
    pension_adjustment_reversal,
    net_past_service_pension_adjustment,
):
    params = get_parameters()["rrsp"]
    limits = {int(y): v for y, v in params["dollar_limit_by_year"].items()}
    year = check_year(limit_year, "Limit year", min(limits), max(limits))
    earned = check_amount(prior_year_earned_income, "Prior-year earned income")
    carried = check_amount(unused_room_carried_forward, "Unused room carried forward")
    pa = check_amount(pension_adjustment, "Pension adjustment")
    par = check_amount(pension_adjustment_reversal, "Pension adjustment reversal")
    pspa = check_amount(net_past_service_pension_adjustment, "Net past service pension adjustment")

    eighteen_percent = round(earned * params["earned_income_rate"], 2)
    dollar_limit = limits[year]
    new_room = min(eighteen_percent, dollar_limit)
    total = round(carried + new_room - pa + par - pspa, 2)
    notes = [
        "Earned income must be the CRA-defined figure for the previous year; this tool does not compute it.",
        "Your Notice of Assessment or CRA My Account shows the official deduction limit and always takes priority.",
    ]
    if total < 0:
        total = 0.0
        notes.append("The formula gave a negative number, so the limit is shown as 0.")
    return finish(
        {
            "limit_year": year,
            "prior_year_earned_income": earned,
            "eighteen_percent_of_earned_income": eighteen_percent,
            "annual_dollar_limit": dollar_limit,
            "new_room_this_year": new_room,
            "unused_room_carried_forward": carried,
            "pension_adjustment": pa,
            "pension_adjustment_reversal": par,
            "net_past_service_pension_adjustment": pspa,
            "rrsp_deduction_limit": total,
            "limited_by": "annual dollar limit" if eighteen_percent > dollar_limit else "18% of earned income",
            "notes": notes,
            "sources": params["source_urls"],
        },
        "formula_estimate",
        get_rules()["tax_year"],
    )


def rrsp_contribution_tax_savings(income, province, contribution, available_room):
    amount = check_amount(income, "Income")
    paid = check_amount(contribution, "Contribution")
    room = None if available_room is None else check_amount(available_room, "Available RRSP room")
    deductible = paid if room is None else min(paid, room)
    if deductible > amount:
        raise ValueError("The deductible contribution cannot be larger than income")
    result = deduction_comparison(amount, province, deductible)
    notes = ["Income must be the amount before the RRSP deduction."]
    if room is None:
        notes.append("Available room was not provided, so the full contribution is assumed deductible.")
    elif paid > room:
        notes.append(
            "The contribution is larger than the available room. Only the part within "
            "room is treated as deductible here; the excess may be an over-contribution, "
            "so check your Notice of Assessment and the CRA rules."
        )
    result.update(
        {
            "contribution": paid,
            "available_rrsp_room": room,
            "deductible_amount": deductible,
            "excess_over_room": round(max(paid - room, 0.0), 2) if room is not None else None,
            "notes": notes,
        }
    )
    result["result_type"] = "formula_estimate"
    return result


def tfsa_contribution_room(
    first_eligible_year,
    as_of_year,
    contributions_to_date,
    withdrawals_before_as_of_year,
):
    params = get_parameters()["tfsa"]
    limits = {int(y): v for y, v in params["annual_limit_by_year"].items()}
    first_year, last_year = min(limits), max(limits)
    start = max(check_year(first_eligible_year, "First eligible year", 1900, last_year), first_year)
    year = check_year(as_of_year, "As-of year", start, last_year)
    contributed = check_amount(contributions_to_date, "Contributions to date")
    withdrawn = check_amount(withdrawals_before_as_of_year, "Withdrawals before the as-of year")

    cumulative = sum(limits[y] for y in range(start, year + 1))
    room = round(cumulative - contributed + withdrawn, 2)
    notes = [
        "Assumes the person was a Canadian resident and at least 18 for every year counted.",
        "Only withdrawals made in earlier calendar years are added back; withdrawals in the as-of year itself are not.",
        "Your CRA My Account shows the official room and always takes priority.",
    ]
    if room < 0:
        notes.append(
            "The result is negative, which suggests an over-contribution. "
            "Check CRA My Account and the CRA rules on TFSA over-contributions."
        )
    return finish(
        {
            "first_year_counted": start,
            "as_of_year": year,
            "cumulative_limit": cumulative,
            "contributions_to_date": contributed,
            "withdrawals_before_as_of_year": withdrawn,
            "available_room": room,
            "annual_limit_in_as_of_year": limits[year],
            "notes": notes,
            "sources": params["source_urls"],
        },
        "formula_estimate",
        get_rules()["tax_year"],
    )
