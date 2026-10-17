"""
This file is the one place in the project that creates the Gemini model, using
LangChain's Google integration (ChatGoogleGenerativeAI). Any other file that
needs a model, such as the assistant agent or, later, the ingestion agent,
simply calls get_model() instead of setting up Gemini itself. The model name is
read from the GEMINI_MODEL setting in your .env file, with a default as a
fallback, and the API key is read automatically from GEMINI_API_KEY, which
load_dotenv() loads from the same .env file.

We need this because it keeps every Gemini setting in one spot. Model names
change often, so if one stops working or you want a cheaper or smarter model,
you edit a single line in .env and the whole project follows. Running the file
directly, with python -m backend.llm, sends a short test message to Gemini so
you can confirm your key, your model name and the LangChain connection all work
before we build anything on top of them.
"""

import os

from dotenv import load_dotenv

# LangChain is the Python library acting as the bridge between my Python code and Google's Gemini API.
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

DEFAULT_MODEL = "gemini-3.8-flash"



# get_model() is a function that prepares my Gemini AI so my Python program can talk to it.
def get_model(**kwargs):
    return ChatGoogleGenerativeAI(
        model=os.environ.get("GEMINI_MODEL", DEFAULT_MODEL),
        **kwargs,
    )


if __name__ == "__main__":
    reply = get_model().invoke("Explain Tokyo in five phrases.")
    print(reply.text)
