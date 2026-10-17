
"""
This file turns our tax calculator into a "tool" that an AI agent can use. The
@tool decorator from LangChain wraps a normal Python function and reads its
name, its typed inputs (income and province) and its docstring, then shows
those to Gemini as a menu item. Gemini never runs the function itself: it only
asks for it, for example "call calculate_income_tax with income 85000 and
province ON", and LangChain runs the real Python code and hands the answer back
to the model.

We need this because of our main rule: the AI must never do tax math. The tool
is the only way the agent can get a tax number, and it always comes from the
deterministic calculator, together with the source links used for citations. If
the agent asks for an unknown province or a negative income, the tool returns
an error message instead of crashing, so the agent can read it and try again or
ask the user. For now the rules come from the JSON file, and we can switch them
to the database later without touching the agent.


Important:
Similarly, we list all the tools that Gemini AI can use in tools.py because Gemini needs to 
know which tools are available, what each tool does, and what inputs it requires. 
LangChain uses these descriptions to help Gemini choose the appropriate tool based on 
the user's question. The actual work is performed by our Python functions, while Gemini 
decides which tool to request.
"""


from langchain.tools import tool

from backend.calculator import calculate_tax, load_rules


@tool
def calculate_income_tax(income: float, province: str) -> dict:
    """Calculate Canadian federal and provincial income tax for the 2026 tax year.

    Use this tool whenever a user asks about:
    - How much income tax they will pay in Canada.
    - Federal, provincial, or total income tax.
    - Income tax for a specific salary or annual taxable income.
    - Comparing income taxes between Canadian provinces.
    - Estimating income tax for different income levels.

    Required inputs:
    - income: Annual taxable income in Canadian dollars (CAD).
    Must be a non-negative number.
    - province: A two-letter Canadian province or territory code.
    Valid codes: NL, PE, NS, NB, QC, ON, MB, SK, AB, BC, YT, NT, NU.

    Location examples:
    - Montreal and Quebec City → QC
    - Toronto and Ottawa → ON
    - Vancouver → BC
    - Calgary and Edmonton → AB
    - Winnipeg → MB
    - Halifax → NS

    The tool returns:
    - Federal income tax before credits.
    - Provincial or territorial income tax before credits.
    - Total income tax before credits.
    - Source URLs for the tax rules used.

    Important instructions:
    - Always use this tool when calculating Canadian income tax.
    - Never calculate or guess tax amounts yourself.
    - Never invent tax brackets, rates, or tax results.
    - Use the tool's returned numbers when explaining calculations.
    - Do not confuse gross annual salary with taxable income.
    - If the user provides monthly income, convert it to annual income
    only when the intended income basis is clear.
    - If the province is missing, ask the user which province they mean.
    - If the income is missing, ask the user for their annual income.
    - If the user provides a city, identify its province when unambiguous.
    - Do not claim that the result includes tax credits, deductions,
    CPP/QPP contributions, EI premiums, or other payroll deductions.
    - If the tool returns an error, explain the problem instead of
    inventing a result.
    - Explain the result clearly in simple language.
    - Clearly state that the result is for the 2026 tax year and
    represents income tax before credits.
    """
    try:
        return calculate_tax(income, province.strip().upper(), load_rules())
    except ValueError as error:
        return {"error": str(error)}