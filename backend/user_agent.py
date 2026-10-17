
"""
This file builds the assistant agent, the part of the project that talks to the
user. It uses LangChain's create_agent, which wraps three things together:
the Gemini model from llm.py, the list of tools the agent is allowed to use
(for now only the tax calculator from tools.py), and a system prompt, which is
the set of rules the agent must follow. When you ask a question, the agent runs
a loop: Gemini reads the question and decides whether to call a tool, LangChain
runs the tool and returns the result, and Gemini then either calls another tool
or writes the final answer. The function ask() returns both the answer and the
list of tool calls, so you can see exactly what the agent decided to do.

We need this because it is the first real agent of the project, and it is where
our main rules are enforced in the prompt: every tax number must come from the
calculator tool, every number must be cited with the source links, the agent
stays on Canadian income tax, and it says it gives general information rather
than tax advice. These prompt rules are soft guardrails, so later we will add
hard checks in code. A recursion limit stops the loop from running forever.
Run it with python -m backend.agent and chat with it in the terminal.
"""

from langchain.agents import create_agent
from langchain.messages import AIMessage

from backend.llm import get_model
from backend.tools import calculate_income_tax



SYSTEM_PROMPT = """
You are a Canadian income tax assistant for the 2026 tax year.

Rules you must always follow:
1. For any tax amount, call the calculate_income_tax tool. Never calculate,
   estimate or recall tax figures yourself.
2. When you state a tax figure, cite the source URLs returned by the tool.
3. The tool returns bracket tax before credits. It does not include the basic
   personal amount, deductions or other credits, so say that the result is not
   a full tax return.
4. Convert cities to provinces (Toronto is in Ontario, Montreal is in Quebec). If the
   province or the income is unclear, ask the user instead of guessing.
5. Only answer questions about Canadian income tax. Politely decline anything
   else.
6. You give general information, not tax advice. For complex situations,
   suggest speaking to a tax professional.
7. If the tool returns an error, explain it simply and ask the user to correct
   the input."""






def build_agent():
    
    # create_agent() is LangChain's function that builds an AI agent capable of using tools.
    return create_agent(
        model=get_model(), # Connects the agent to Gemini using the llm.py 
        tools=[calculate_income_tax], # Gives Gemini access to your tax calculator tool from tools.py.
        system_prompt=SYSTEM_PROMPT, # Gives Gemini instructions about how to behave, such as never guessing tax calculations.
    )


def ask(agent, question):
    result = agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config={"recursion_limit": 10},
    )
    tool_calls = []
    for message in result["messages"]:
        if isinstance(message, AIMessage) and message.tool_calls:
            tool_calls.extend(message.tool_calls)
    return result["messages"][-1].text, tool_calls


def main():
    agent = build_agent()
    
    print("-" * 100)
    print("Welcome to Ratios — Your AI-Powered Canadian Tax Assistant")
    print("-" * 100)
    print("Ask questions about Canadian federal and provincial income taxes.")
    print("Calculate income taxes and explore different tax scenarios.")
    print("Type 'quit' at any time to exit.")
    print("-" * 100)
    while True:
        question = input("\nYou: ").strip()
        if question.lower() in {"quit", "exit"}:
            break
        if not question:
            continue
        answer, tool_calls = ask(agent, question)
        for call in tool_calls:
            print(f"  [tool call] {call['name']}({call['args']})")
        print(f"\nAssistant: {answer}")


if __name__ == "__main__":
    main()