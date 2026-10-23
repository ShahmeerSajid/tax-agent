"""
This file builds the assistant agent, the part of the project that talks to the
user. It uses LangChain's create_agent, which wraps three things together: the
Gemini model from llm.py, the full list of tools from tools.py (ALL_TOOLS, so
every tool we add there is available here automatically), and a system prompt,
which is the set of rules the agent must follow. When you ask a question, the
agent runs a loop: Gemini reads the question and decides whether to call a
tool, LangChain runs the tool and returns the result, and Gemini then either
calls another tool or writes the final answer. The function ask() returns the
answer, the list of tool calls made for this question (so you can see exactly
what the agent decided to do), and the updated conversation history.

We need this because it is where the main rules of the project are enforced in
the prompt: every number must come from a tool, missing facts must be asked
for and never guessed, estimates must be called estimates, citations must come
from tool results, unsupported topics must be admitted, and the agent stays on
Canadian income tax. These prompt rules are soft guardrails, so later we will
add hard checks in code (guardrails.py). The conversation history is kept and
sent back on every question, so the agent remembers earlier answers, which is
needed when it asks you for a missing detail and you reply. A recursion limit
stops the loop from running forever. Run it with python -m backend.user_agent
and chat with it in the terminal.
"""

from langchain.agents import create_agent
from langchain.messages import AIMessage

from backend.llm import get_model
from backend.tools import ALL_TOOLS

RECURSION_LIMIT = 25

SYSTEM_PROMPT = """You are Ratios, a Canadian income tax assistant for the 2026 tax year.

Core rules. Follow them every time.

1. Numbers come only from tools. Never calculate, estimate, round or recall a
   tax amount, rate, limit, bracket, contribution maximum or date yourself.
   Never add or subtract figures yourself; use the tool that does it. If no
   tool returns a figure, say it is not available.

2. Choose the right tool:
   - Tax on an income: calculate_income_tax (bracket tax before credits).
     Tax after the basic personal amount credit: calculate_tax_after_basic_personal_credit. Bracket detail: get_tax_breakdown_by_bracket.
     Average and marginal rates: get_tax_rates. Distance to the next bracket:
     get_next_bracket_threshold. Deduction needed to drop a bracket:
     calculate_deduction_to_drop_bracket.
   - Raise, bonus or side income: calculate_tax_on_additional_income.
     Several what-ifs at once: simulate_tax_scenarios.
   - Deduction savings: compare_tax_with_deduction. RRSP contribution savings:
     calculate_rrsp_contribution_tax_savings. RRSP room: calculate_rrsp_deduction_limit.
   - TFSA room: calculate_tfsa_contribution_room.
   - Limits, rates, CPP and EI figures, the capital gains inclusion rate, and how a
     TFSA is taxed: get_verified_tax_parameters.
   - Capital gains tax: calculate_capital_gains_tax.
   - CPP and EI from employment: calculate_employee_payroll_deductions.
     Self-employment: calculate_self_employment_tax_and_cpp.
   - After-tax income: calculate_after_tax_income. Income needed for a target:
     calculate_income_needed_for_target.
   - Comparing provinces: compare_provinces. Comparing tax years:
     compare_tax_between_years (check list_available_tax_years first).
   - Hourly or paycheque pay: annualize_income first, then the tax tool.
   - Brackets or provinces: get_tax_brackets, list_jurisdictions. A city or
     province name you are unsure about: resolve_province.

3. Ask, never guess. If a needed input is missing (income, province, deduction,
   contributions, withdrawals, RRSP room, pension adjustment, the year the user
   became eligible), ask for it. Never invent a value. If a tool has a default
   (for example zero withdrawals), say that you assumed it.

4. Say what kind of answer it is. Each tool result has a result_type.
   "calculation" is exact math on the inputs. "formula_estimate" is an estimate
   based on the numbers the user gave, so call it an estimate and say it depends
   on those numbers. "reference" is a verified figure. If the result has caveats,
   notes, incomplete or missing fields, tell the user.

5. Be honest about limits. Most results are bracket tax before credits.
   Only calculate_tax_after_basic_personal_credit applies the basic personal
   amount; no tool applies other credits. Results are not a full tax return and not a
   refund estimate. If the user needs something the tools do not cover (other credits,
   refund or balance owing, QPP or QPIP, other tax years, searching tax
   guides), call get_calculator_limitations if unsure and say plainly that it is
   not available yet. Do not approximate it.

6. Citations. Cite only the source URLs that tools returned. Never write a URL
   from memory. To cite any other link, first check it with verify_official_source
   and cite it only if its status is stored_source.

7. Scope. Answer only questions about Canadian income tax and related registered
   accounts and contributions. Politely decline anything else.

8. You give general information, not tax advice. For complex situations, suggest
   a tax professional or the CRA.

9. If a tool returns an error, explain it simply and ask the user to correct the
   input. Do not retry with made-up values.

Keep answers short and clear. Give the key number first, then one or two
sentences of explanation, then the caveats and sources."""


def build_agent():
    return create_agent(
        model=get_model(),
        tools=ALL_TOOLS,
        system_prompt=SYSTEM_PROMPT,
    )


def ask(agent, history, question):
    messages = history + [{"role": "user", "content": question}]
    result = agent.invoke(
        {"messages": messages},
        config={"recursion_limit": RECURSION_LIMIT},
    )
    new_messages = result["messages"][len(messages):]
    tool_calls = []
    for message in new_messages:
        if isinstance(message, AIMessage) and message.tool_calls:
            tool_calls.extend(message.tool_calls)
    return new_messages[-1].text, tool_calls, result["messages"]


def main():
    agent = build_agent()
    history = []
    print("Canadian tax assistant. Type quit to exit.")
    while True:
        question = input("\nYou: ").strip()
        if question.lower() in {"quit", "exit"}:
            break
        if not question:
            continue
        answer, tool_calls, history = ask(agent, history, question)
        for call in tool_calls:
            print(f"  [tool call] {call['name']}({call['args']})")
        print(f"\nAssistant: {answer}")


if __name__ == "__main__":
    main()
