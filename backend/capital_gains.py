"""
This file calculates the income tax on capital gains. In Canada only part of a
capital gain (the inclusion rate) is added to taxable income, so the extra tax
is the difference between the tax on the person's other income plus that
taxable portion and the tax on the other income alone, both computed with the
same federal and provincial bracket calculator used everywhere else. Capital
losses in the same year are subtracted from the gains first. A net loss
produces no tax and does not reduce other income in this tool.

We need this because the gain is taxed at the person's marginal rates, not a
flat rate, and an AI model would otherwise guess the percentage. The inclusion
rate is read from data/tax_parameters_2026.json together with its official
sources and a note about the cancelled proposal to raise it, so the rate is
never typed into a prompt. The result is a calculation on the numbers the user
gave, but it leaves out the principal residence exemption, the lifetime
capital gains exemption, loss carry-overs, the alternative minimum tax and
credits, and the result says so.
"""

from backend.calculator import calculate_tax
from backend.common import caveats, check_amount, finish, get_parameters, get_rules, normalize_province


def capital_gains_tax(income, province, capital_gains, capital_losses):
    rules = get_rules()
    params = get_parameters()["capital_gains"]
    other_income = check_amount(income, "Other taxable income")
    gains = check_amount(capital_gains, "Capital gains")
    losses = check_amount(capital_losses, "Capital losses")
    code = normalize_province(province, rules)

    rate = params["inclusion_rate"]
    net_gain = round(gains - losses, 2)
    taxable_gain = round(max(net_gain, 0.0) * rate, 2)
    before = calculate_tax(other_income, code, rules)
    after = calculate_tax(other_income + taxable_gain, code, rules)
    extra_tax = round(after["total_tax"] - before["total_tax"], 2)

    notes = [
        params["note"],
        "Not modelled: principal residence exemption, lifetime capital gains exemption, "
        "loss carry-overs, alternative minimum tax and credits.",
    ]
    if net_gain < 0:
        notes.append(
            "There is a net capital loss. It does not create tax this year and is not "
            "applied against other income in this tool."
        )
    return finish(
        {
            "other_taxable_income": other_income,
            "province": code,
            "capital_gains": gains,
            "capital_losses": losses,
            "net_capital_gain": net_gain,
            "inclusion_rate": rate,
            "taxable_capital_gain": taxable_gain,
            "tax_without_gain": before["total_tax"],
            "tax_with_gain": after["total_tax"],
            "tax_on_capital_gain": extra_tax,
            "gain_kept_after_tax": round(max(net_gain, 0.0) - extra_tax, 2),
            "caveats": caveats(code),
            "notes": notes,
            "sources": before["sources"] + params["source_urls"],
        },
        "calculation",
        rules["tax_year"],
    )
