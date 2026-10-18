"""


PURPOSE OF tools.py:

This file connects our Python functions to the Gemini AI agent using LangChain.
Tools allow Gemini AI to perform real tasks using Python functions, such as calculating taxes, 
searching documents, or retrieving information from a database. LangChain does not decide 
which tool Gemini should use. Instead, LangChain provides Gemini with a list of available tools,
including their names, descriptions, and required inputs. Gemini reads these descriptions and 
decides which tool is appropriate for the user's question. LangChain then executes the requested
Python function in your backend and sends the result back to Gemini, which explains it to the 
user. In simple words, Gemini makes the decision, LangChain connects everything, and your 
Python functions do the actual work.

Our backend contains functions that perform actual tasks, such as calculating
income tax, searching documents, and retrieving information from Neon.

However, Gemini cannot automatically access these functions. We use LangChain's
@tool decorator to expose them to the AI.

Each tool has a name, input parameters, and a docstring explaining what it does.
LangChain shares this information with Gemini so it knows which tools are available
and when to use them.

HOW IT WORKS:
1. The user asks Gemini a question through our backend.
2. Gemini examines the available tools and chooses the appropriate one.
3. Gemini requests the tool with the required arguments.
4. LangChain executes the corresponding Python function in our backend.
5. The function performs the task and returns its result.
6. Gemini receives the result and explains it to the user.

IMPORTANT:
Gemini decides WHICH tool to request, but our Python backend performs the
actual work. tools.py acts as the bridge between the AI and our backend functions.

Therefore, we list all the tools that Gemini AI can use in tools.py because Gemini needs to 
know which tools are available, what each tool does, and what inputs it requires. 
LangChain uses these descriptions to help Gemini choose the appropriate tool based on 
the user's question. The actual work is performed by our Python functions, while Gemini 
decides which tool to request.


This file is the central registry of every tool the assistant agent can call.
Each function decorated with @tool is a menu item that LangChain shows to
Gemini: the model reads the tool's name, its typed inputs and its docstring,
then asks for a tool by name, and LangChain runs the real Python code and hands
the result back. The model never runs anything itself, never does tax math and
never supplies a tax figure of its own. The tools here are deliberately thin:
each one only describes itself to the model and calls a function in a logic
module (core_tax, savings_accounts, capital_gains, payroll, scenarios,
tax_years, reference), where the validation and the math live and can be
tested without LangChain or Gemini. Bad input never crashes a tool; it returns
{"error": "..."} so the agent can ask the user to correct it.

Every result carries a result_type so the agent can say honestly what kind of
answer it is: "calculation" (exact rule-based math on the inputs),
"formula_estimate" (a published formula applied to numbers the user typed in,
with stated assumptions) or "reference" (a verified figure or fact looked up
from our files). The tools are grouped into lists (LOOKUP_TOOLS, CORE_TAX_TOOLS,
WHAT_IF_TOOLS, SAVINGS_TOOLS, INCOME_TOOLS, TAX_YEAR_TOOLS) and joined in
ALL_TOOLS, which the agent imports; to add a tool later, write the logic in a
module, add a small @tool wrapper here, and append it to one group. Features
that cannot be built honestly yet (tax credits, refund estimates, QPP and QPIP,
document search with RAG, prior-year rules) are not faked: they are listed by
get_calculator_limitations as missing dependencies.
"""



from langchain.tools import tool

from backend import core_tax, payroll, reference, savings_accounts, tax_years
from backend.capital_gains import capital_gains_tax
from backend.scenarios import Scenario, simulate_scenarios







def _run(function, *args):
    try:
        return function(*args)
    except ValueError as error:
        return {"error": str(error)}






@tool
def list_jurisdictions() -> dict:
    """List every jurisdiction the calculator supports.

    Purpose: returns the federal government plus each province and territory
    with its two-letter code, its name and the official source URL of its
    brackets.
    Use when: the user asks which provinces or territories are covered, or you
    need to check a code.
    Inputs: none.
    Returns: result_type "reference", the tax year and a list of
    {code, name, source_url}.
    Limits: only the tax year loaded in the rules (2026).
    Instructions: do not list jurisdictions from memory."""
    return _run(core_tax.list_jurisdictions)





@tool
def resolve_province(location: str) -> dict:
    """Turn a city, province name or code into a two-letter jurisdiction code.

    Purpose: removes guessing when the user says a city such as Toronto or
    Montreal.
    Use when: the user names a city or full province name and you are not
    completely sure of the code.
    Inputs: location, for example 'Toronto', 'Quebec' or 'Calgary, AB'.
    Returns: {input, province, name}, or an error if the place is unknown.
    Limits: knows about 100 major cities; any other place returns an error.
    Instructions: if it returns an error, ask the user which province they live
    in. Never guess a province."""
    return _run(core_tax.resolve_province, location)




@tool
def get_tax_brackets(jurisdiction: str) -> dict:
    """Return the 2026 income tax brackets of the federal government or one province.

    Purpose: shows each bracket's lower limit, upper limit and rate with the
    official source URL.
    Use when: the user asks what the brackets or rates are. Do not use it to
    compute a tax amount.
    Inputs: jurisdiction, either 'federal' or a province code, name or city.
    Returns: result_type "reference", brackets as {from, to, rate,
    rate_percent} (to is null for the top bracket), caveats and sources.
    Limits: brackets only; credits and surtaxes are not part of this list.
    Instructions: quote only the numbers returned and cite the source URL."""
    return _run(core_tax.get_tax_brackets, jurisdiction)




@tool
def get_calculator_limitations() -> dict:
    """Return what the assistant's tools include and what they do NOT include.

    Purpose: gives the honest list of known gaps and missing dependencies, such
    as tax credits, the basic personal amount, refund estimates, QPP and QPIP,
    the Ontario surtax, the Quebec abatement, prior years and document search.
    Use when: the user asks how accurate a result is, whether it is their real
    tax bill, or asks for something that may not be supported.
    Inputs: none.
    Returns: lists named included and not_included_or_not_available.
    Instructions: if a request needs something in the not-available list, say
    so plainly. Never approximate it yourself."""
    return _run(core_tax.calculator_limitations)





@tool
def get_verified_tax_parameters(topic: str) -> dict:
    """Return verified 2026 figures: RRSP, TFSA, CPP, EI and capital gains inclusion rate.

    Purpose: the only allowed source for limits, ceilings, premium rates, the
    capital gains inclusion rate and the TFSA tax treatment (growth and
    withdrawals are generally tax-free). Each section lists the official CRA
    pages it was read from.
    Use when: the user asks for a limit or rate, for example 'what is the RRSP
    limit' or 'what is the CPP maximum'.
    Inputs: topic, one of 'rrsp', 'tfsa', 'cpp', 'ei', 'capital_gains', 'all'.
    Returns: result_type "reference" with the stored parameters and a note.
    Limits: only the figures stored in the project; anything else is not
    available.
    Instructions: quote only what is returned and cite its source URLs. If a
    figure is not returned, say it is not available."""
    return _run(reference.verified_parameters, topic)





@tool
def verify_official_source(url: str) -> dict:
    """Check whether a link is an official source that the project actually stored.

    Purpose: stops invented citations. Compares the link with an allowlist of
    official domains (canada.ca, gc.ca, revenuquebec.ca) and with the source
    links recorded in our rules and parameters.
    Use when: you want to cite a link that did not come from a tool result, or
    the user asks whether a link is official.
    Inputs: url, a full https:// address.
    Returns: status 'stored_source', 'official_domain_not_stored' or
    'not_official', plus what the link was used for.
    Limits: it does not open the page, so it cannot confirm the page content;
    page_content_checked is always false.
    Instructions: only cite links whose status is 'stored_source'. Never make
    up a URL."""
    return _run(reference.verify_source, url)





@tool
def calculate_income_tax(income: float, province: str) -> dict:
    """Calculate 2026 federal plus provincial income tax before credits.

    Purpose: the main tax calculator. Applies marginal brackets to an annual
    taxable income.
    Use when: the user asks what tax they pay on an income in a province.
    Inputs: income (annual taxable income in dollars) and province (code such
    as ON, a province name or a major city).
    Returns: result_type "calculation", federal_tax, provincial_tax,
    total_tax, average_rate, caveats and source URLs.
    Limits: bracket tax only. No credits (not even the basic personal amount),
    no CPP or EI, no Ontario surtax or Health Premium, no Quebec abatement.
    Instructions: always use this tool for any tax amount; never estimate tax
    yourself. Tell the user the result is before credits and not a tax return,
    and cite the sources."""
    return _run(core_tax.income_tax, income, province)





@tool
def get_tax_breakdown_by_bracket(income: float, province: str) -> dict:
    """Show how the tax is built up bracket by bracket, federal and provincial.

    Purpose: explains how much income falls in each bracket, at what rate, and
    what tax it produces.
    Use when: the user asks how the tax was calculated or wants to understand
    marginal brackets.
    Inputs: income (annual, dollars) and province.
    Returns: result_type "calculation", the reached brackets for federal and
    provincial tax, each tax total and the overall total.
    Limits: same as calculate_income_tax; rows can differ from a total by a
    cent because of rounding.
    Instructions: use the totals returned; do not add the rows yourself."""
    return _run(core_tax.breakdown, income, province)






@tool
def get_tax_rates(income: float, province: str) -> dict:
    """Return the average tax rate and the marginal rates at an income.

    Purpose: shows the average (effective) rate and the marginal rate, which is
    the tax rate on the next dollar earned (federal, provincial and combined).
    Use when: the user asks about their tax rate, their bracket, or what
    percentage of a raise or bonus is taxed.
    Inputs: income (annual, dollars) and province.
    Returns: result_type "calculation", average_rate, federal, provincial and
    combined marginal rates, and the current bracket limits.
    Limits: the combined marginal rate adds the two bracket rates only; the
    Ontario surtax and the Quebec abatement are not modelled, so the true
    marginal rate in those provinces differs (the caveats say so).
    Instructions: report rates as returned and mention any caveat."""
    return _run(core_tax.tax_rates, income, province)





@tool
def get_next_bracket_threshold(income: float, province: str) -> dict:
    """Tell how many dollars of income remain before the next bracket starts.

    Purpose: shows the next federal and provincial bracket threshold, how far
    away it is, and the rate before and after.
    Use when: the user asks how close they are to the next bracket.
    Inputs: income (annual, dollars) and province.
    Returns: result_type "calculation" with federal_next_bracket and
    provincial_next_bracket; null means already in the top bracket.
    Limits: brackets only.
    Instructions: use the returned numbers; do not subtract yourself."""
    return _run(core_tax.next_threshold, income, province)






@tool
def calculate_deduction_to_drop_bracket(income: float, province: str) -> dict:
    """Find how large a deduction must be so no income is taxed in the current bracket.

    Purpose: for each of federal and provincial tax, returns the amount of
    income taxed at the current bracket's rate (the deduction needed to stop
    that), the rate now and the rate of the bracket below.
    Use when: the user asks how much RRSP or other deduction would bring them
    down a bracket.
    Inputs: income (annual, dollars) and province.
    Returns: result_type "calculation" with federal_drop and provincial_drop;
    null means already in the lowest bracket.
    Limits: assumes the deduction reduces taxable income dollar for dollar; the
    user's actual deduction room (such as RRSP room) is not checked here.
    Instructions: if the deduction is an RRSP contribution, also check room
    with calculate_rrsp_deduction_limit or ask the user for their room."""
    return _run(core_tax.deduction_to_drop_bracket, income, province)





@tool
def compare_provinces(income: float, provinces: list[str] | None = None) -> dict:
    """Compare total income tax at the same income across provinces, ranked low to high.

    Purpose: shows where the same income is taxed least, with each province's
    difference from the cheapest.
    Use when: the user asks 'where do I pay the least tax' or compares
    provinces such as Ontario and Alberta.
    Inputs: income (annual, dollars) and provinces, a list of codes, names or
    cities; leave empty to compare all provinces and territories.
    Returns: result_type "calculation", ranked rows with federal, provincial
    and total tax and average rate.
    Limits: bracket tax before credits. Quebec is not reliable because its
    federal abatement is not applied; provincial credits are not applied.
    Instructions: point out the caveats; do not say a province is 'cheapest to
    live in', only that its bracket tax is lowest."""
    return _run(core_tax.compare_provinces, income, provinces)






@tool
def annualize_income(
    amount: float,
    period: str,
    hours_per_week: float = 40.0,
    weeks_per_year: float = 52.0,
) -> dict:
    """Convert hourly, weekly, biweekly, semi-monthly, monthly pay into a yearly income.

    Purpose: gives the annual income that the other tools need.
    Use when: the user gives an hourly wage or a paycheque instead of a yearly
    salary.
    Inputs: amount (dollars), period ('hourly', 'weekly', 'biweekly',
    'semi-monthly', 'monthly' or 'annual'), and for hourly pay hours_per_week
    (default 40) and weeks_per_year (default 52).
    Returns: result_type "calculation", annual_income and how it was computed.
    Limits: assumes constant pay, no overtime or unpaid weeks unless given.
    Instructions: never multiply pay yourself; ask for hours if they differ."""
    return _run(core_tax.annualize, amount, period, hours_per_week, weeks_per_year)





@tool
def compare_tax_with_deduction(income: float, province: str, deduction: float) -> dict:
    """Compare tax with and without a deduction, and report the tax saved.

    Purpose: shows how much a deduction lowers federal plus provincial tax.
    Use when: the user asks what a deduction saves. For RRSP questions prefer
    calculate_rrsp_contribution_tax_savings, which also checks room.
    Inputs: income (annual, dollars), province, deduction (zero or more, not
    larger than income).
    Returns: result_type "calculation", tax_without_deduction,
    tax_with_deduction and tax_saved.
    Limits: assumes the deduction is allowed in full; eligibility is not checked.
    Instructions: never estimate the savings yourself."""
    return _run(core_tax.deduction_comparison, income, province, deduction)





@tool
def calculate_tax_on_additional_income(
    income: float, province: str, additional_income: float
) -> dict:
    """Work out the extra tax on a raise, bonus or side income and how much is kept.

    Purpose: compares tax before and after adding income on top of the current
    income.
    Use when: the user asks 'if I get a $10,000 raise, how much do I keep'.
    Inputs: income (current annual income), province, additional_income (zero
    or more).
    Returns: result_type "calculation" with tax_before, tax_after, extra_tax,
    amount_kept and the tax rate on the additional income.
    Limits: bracket tax only; CPP, EI and credits are not applied.
    Instructions: say 'before CPP, EI and credits' when reporting what is kept."""
    return _run(core_tax.additional_income, income, province, additional_income)







@tool
def calculate_after_tax_income(income: float, province: str) -> dict:
    """Return income minus bracket tax per year, month and two weeks.

    Purpose: a rough 'what is left after income tax' figure.
    Use when: the user asks for after-tax or take-home income and accepts an
    approximation.
    Inputs: income (annual, dollars) and province.
    Returns: result_type "formula_estimate" with total_tax and yearly, monthly
    and biweekly after-tax income.
    Limits: not real take-home pay. CPP, EI, credits and other deductions are
    not applied. For payroll amounts use calculate_employee_payroll_deductions.
    Instructions: always call it an approximation."""
    return _run(core_tax.after_tax_income, income, province)






@tool
def calculate_income_needed_for_target(target_after_tax_income: float, province: str) -> dict:
    """Find the yearly income needed to be left with a target amount after bracket tax.

    Purpose: works backwards from a wanted after-tax amount using the same
    calculator.
    Use when: the user asks 'how much must I earn to have $60,000 after tax'.
    Inputs: target_after_tax_income (dollars) and province.
    Returns: result_type "formula_estimate" with income_needed, the tax at that
    income and the resulting after-tax income.
    Limits: same approximation as calculate_after_tax_income.
    Instructions: call it an approximation; do not solve it yourself."""
    return _run(core_tax.income_needed, target_after_tax_income, province)







@tool
def simulate_tax_scenarios(
    province: str, base_income: float, scenarios: list[Scenario]
) -> dict:
    """Run several what-if scenarios side by side and compare each with a base case.

    Purpose: compares combinations of income changes and deductions in one call.
    Use when: the user asks about more than one what-if, for example a raise
    with and without an RRSP contribution, or earning less next year.
    Inputs: province, base_income (annual, dollars) and scenarios, a list of up
    to 10 items, each with label, income_change (can be negative) and
    deduction (zero or more).
    Returns: result_type "calculation" with the base tax and, for each
    scenario, taxable income, federal, provincial and total tax, average rate
    and tax_change_vs_base.
    Limits: bracket tax before credits; deductions are assumed allowed.
    Instructions: copy numbers from the result; do not compute differences."""
    return _run(simulate_scenarios, province, base_income, scenarios)


@tool
def calculate_rrsp_deduction_limit(
    prior_year_earned_income: float,
    limit_year: int = 2026,
    unused_room_carried_forward: float = 0.0,
    pension_adjustment: float = 0.0,
    pension_adjustment_reversal: float = 0.0,
    net_past_service_pension_adjustment: float = 0.0,
) -> dict:
    """Estimate a person's RRSP deduction limit with the CRA formula.

    Purpose: unused room carried forward, plus the lesser of 18% of last year's
    earned income and the annual dollar limit, minus pension adjustment and
    net past service pension adjustment, plus any pension adjustment reversal.
    Use when: the user asks how much RRSP room they have or will have.
    Inputs: prior_year_earned_income (CRA earned income of the year before
    limit_year), limit_year (2024 to 2027, default 2026), and optional
    unused_room_carried_forward, pension_adjustment,
    pension_adjustment_reversal and net_past_service_pension_adjustment, all
    from the user's Notice of Assessment or T4 slips.
    Returns: result_type "formula_estimate" with the 18% amount, the dollar
    limit, the limit that applied and the resulting rrsp_deduction_limit.
    Limits: does not calculate earned income and cannot know carry-forward or
    pension figures; the official room is on the Notice of Assessment or CRA My
    Account and always takes priority.
    Instructions: ask the user for missing figures; never assume carry-forward
    or pension adjustment values; call the result an estimate."""
    return _run(
        savings_accounts.rrsp_deduction_limit,
        prior_year_earned_income,
        limit_year,
        unused_room_carried_forward,
        pension_adjustment,
        pension_adjustment_reversal,
        net_past_service_pension_adjustment,
    )


@tool
def calculate_rrsp_contribution_tax_savings(
    income: float,
    province: str,
    contribution: float,
    available_rrsp_room: float | None = None,
) -> dict:
    """Calculate the income tax saved by an RRSP contribution, checked against room.

    Purpose: runs the same with-and-without comparison as
    compare_tax_with_deduction, but only for the part of the contribution that
    fits in the available RRSP room.
    Use when: the user asks how much tax an RRSP contribution saves.
    Inputs: income (annual income before the RRSP deduction), province,
    contribution (dollars) and available_rrsp_room (from the Notice of
    Assessment; omit if unknown).
    Returns: result_type "formula_estimate" with tax_saved, deductible_amount,
    excess_over_room and notes.
    Limits: does not know the user's real room unless provided; an excess over
    room is flagged only, with no penalty calculated; tax is bracket tax before
    credits.
    Instructions: ask for the room if it was not given; never invent it."""
    return _run(
        savings_accounts.rrsp_contribution_tax_savings,
        income,
        province,
        contribution,
        available_rrsp_room,
    )





@tool
def calculate_tfsa_contribution_room(
    first_eligible_year: int,
    as_of_year: int = 2026,
    contributions_to_date: float = 0.0,
    withdrawals_before_as_of_year: float = 0.0,
) -> dict:
    """Estimate TFSA contribution room from the official annual limits.

    Purpose: adds the official annual limits from the first eligible year to
    the as-of year, subtracts contributions and adds back earlier withdrawals.
    Use when: the user asks how much TFSA room they have.
    Inputs: first_eligible_year (the year they turned 18 or became a Canadian
    resident, if later than 2009; years before 2009 count as 2009), as_of_year
    (default 2026), contributions_to_date (total contributed) and
    withdrawals_before_as_of_year (total withdrawn in earlier calendar years).
    Returns: result_type "formula_estimate" with cumulative_limit,
    available_room, the annual limit and notes; a negative room is flagged as a
    possible over-contribution.
    Limits: assumes residency for every counted year; the CRA's own records,
    shown in CRA My Account, always take priority.
    Instructions: ask for missing inputs; never guess contributions."""
    return _run(
        savings_accounts.tfsa_contribution_room,
        first_eligible_year,
        as_of_year,
        contributions_to_date,
        withdrawals_before_as_of_year,
    )


@tool
def calculate_capital_gains_tax(
    income: float,
    province: str,
    capital_gains: float,
    capital_losses: float = 0.0,
) -> dict:
    """Calculate the extra income tax caused by capital gains.

    Purpose: applies the inclusion rate to net capital gains, adds that taxable
    part to other income and reports the extra federal plus provincial tax.
    Use when: the user sold investments or property at a gain and asks for the
    tax.
    Inputs: income (other taxable income, not counting the gain), province,
    capital_gains and capital_losses (same-year, zero or more, in dollars).
    Returns: result_type "calculation" with net gain, inclusion rate, taxable
    gain, tax_with_gain, tax_without_gain, tax_on_capital_gain and sources.
    Limits: no principal residence exemption, lifetime capital gains
    exemption, loss carry-overs or alternative minimum tax; no credits.
    The inclusion rate comes from verified parameters and its note says to
    confirm the current rate with the CRA.
    Instructions: mention the exclusions and the note; do not use any rate of
    your own."""
    return _run(capital_gains_tax, income, province, capital_gains, capital_losses)


@tool
def calculate_employee_payroll_deductions(
    annual_employment_income: float, province: str
) -> dict:
    """Calculate employee CPP, CPP2 and EI amounts and the employer's matching side.

    Purpose: applies the verified 2026 contribution rates, ceilings and
    maximums to employment income.
    Use when: the user asks what CPP or EI is deducted from their pay.
    Inputs: annual_employment_income (dollars) and province.
    Returns: result_type "formula_estimate" with the employee cpp, cpp2, ei,
    total_listed, employer_matching, notes and sources.
    Limits: assumes a full year, one employer, age 18 to 69, no exemptions. For
    Quebec only EI is returned; QPP and QPIP are missing and the result is
    marked incomplete. Income tax is not included.
    Instructions: if incomplete is true, say which parts are missing and do not
    estimate them."""
    return _run(payroll.employee_payroll_deductions, annual_employment_income, province)


@tool
def calculate_self_employment_tax_and_cpp(
    gross_revenue: float, business_expenses: float, province: str
) -> dict:
    """Calculate net business income, its income tax and self-employed CPP.

    Purpose: for a self-employed person, works out revenue minus expenses, the
    federal plus provincial bracket tax on it, and the self-employed CPP and
    CPP2 amounts.
    Use when: the user is self-employed or a sole proprietor and asks about
    tax or CPP.
    Inputs: gross_revenue and business_expenses (dollars, zero or more) and
    province.
    Returns: result_type "formula_estimate" with net_business_income,
    federal_tax, provincial_tax, income_tax_before_credits, self_employed_cpp,
    self_employed_cpp2 and notes.
    Limits: does not decide which expenses are deductible, and ignores the CPP
    deduction and credit, GST/HST, instalments, other income and credits. Not
    calculated for Quebec CPP (QPP is missing; the result is marked
    incomplete).
    Instructions: never judge whether an expense is deductible; tell the user
    to check CRA guidance or a professional."""
    return _run(
        payroll.self_employment_tax, gross_revenue, business_expenses, province
    )


@tool
def list_available_tax_years() -> dict:
    """List the tax years that have brackets stored in the database.

    Purpose: tells the agent which years can be compared.
    Use when: the user asks about a tax year other than 2026, or before
    comparing years.
    Inputs: none.
    Returns: result_type "reference" with available_years.
    Limits: needs DATABASE_URL and the Neon database; today only 2026 is
    loaded, and prior-year data is a missing dependency.
    Instructions: if a year is not listed, say it is not available; never use
    rates from memory for other years."""
    return _run(tax_years.available_years)


@tool
def compare_tax_between_years(
    income: float, province: str, year_a: int, year_b: int
) -> dict:
    """Compare the tax on the same income in two tax years using stored brackets.

    Purpose: shows how bracket changes alter tax between years.
    Use when: the user asks how their tax changed from one year to another.
    Inputs: income (annual, dollars), province, year_a and year_b.
    Returns: result_type "calculation" with each year's federal, provincial and
    total tax and the difference (year_b minus year_a).
    Limits: works only for years stored in the database. If a year is missing it
    returns an error naming the stored years. Bracket tax before credits.
    Instructions: if it returns an error, tell the user which years are
    available and that earlier years are not loaded yet. Never fill the gap
    from memory."""
    return _run(tax_years.compare_years, income, province, year_a, year_b)


LOOKUP_TOOLS = [
    list_jurisdictions,
    resolve_province,
    get_tax_brackets,
    get_calculator_limitations,
    get_verified_tax_parameters,
    verify_official_source,
]

CORE_TAX_TOOLS = [
    calculate_income_tax,
    get_tax_breakdown_by_bracket,
    get_tax_rates,
    get_next_bracket_threshold,
    calculate_deduction_to_drop_bracket,
    compare_provinces,
    annualize_income,
]

WHAT_IF_TOOLS = [
    compare_tax_with_deduction,
    calculate_tax_on_additional_income,
    calculate_after_tax_income,
    calculate_income_needed_for_target,
    simulate_tax_scenarios,
]

SAVINGS_TOOLS = [
    calculate_rrsp_deduction_limit,
    calculate_rrsp_contribution_tax_savings,
    calculate_tfsa_contribution_room,
]

INCOME_TOOLS = [
    calculate_capital_gains_tax,
    calculate_employee_payroll_deductions,
    calculate_self_employment_tax_and_cpp,
]

TAX_YEAR_TOOLS = [
    list_available_tax_years,
    compare_tax_between_years,
]

ALL_TOOLS = (
    LOOKUP_TOOLS
    + CORE_TAX_TOOLS
    + WHAT_IF_TOOLS
    + SAVINGS_TOOLS
    + INCOME_TOOLS
    + TAX_YEAR_TOOLS
)
