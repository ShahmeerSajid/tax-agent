# Ratios AI: Full-Stack Agentic AI Canadian Tax Assistant

Ratios is a full-stack, agentic AI platform designed to simplify Canadian income taxation through natural-language interactions, automated tax-rule extraction, and deterministic financial calculations. The system combines LLM-based tool calling, Retrieval-Augmented Generation (RAG), and a verified tax calculation engine to provide explainable, source-grounded answers to federal and provincial tax questions.

## System Architecture

Ratios is organized into three AI agents and a deterministic Python tax engine.

### 1. Tax Rule Ingestion Agent

An automated ingestion pipeline retrieves publicly available tax information from official CRA and provincial government sources.

- **Data collection:** Python-based HTTPX, BeautifulSoup, and Playwright tools retrieve HTML content and relevant tax documents.
- **Change detection:** Content hashing identifies modified government pages to avoid unnecessary reprocessing.
- **Structured extraction:** Gemini extracts tax brackets, marginal rates, deductions, and credits into structured JSON validated using Pydantic.
- **Scheduling:** GitHub Actions periodically executes the ingestion pipeline without requiring a continuously running local machine.

### 2. Tax Rule Verification Agent

A second AI agent independently checks extracted information against official sources, validating tax years, jurisdictions, rates, and supporting references.

- Detects inconsistencies and potentially outdated regulations.
- Stores proposed rule changes in PostgreSQL for review.
- Requires human approval through an administrative dashboard before activating updated tax rules.
- Maintains source references and rule versions for traceability.

### 3. User Assistant Agent

A Gemini-powered assistant handles user queries through an agentic tool-calling workflow.

- **Tool selection:** Gemini interprets natural-language questions and generates structured function calls.
- **RAG retrieval:** User queries are embedded using Gemini Embeddings and matched against stored document vectors using PostgreSQL's `pgvector` extension.
- **Tax calculations:** The assistant invokes Python calculator functions that retrieve approved tax rules and apply progressive federal and provincial tax brackets.
- **Scenario analysis:** Supports comparisons such as different income levels, provinces, and RRSP contribution scenarios.
- **Response generation:** Retrieved documentation and calculator outputs are returned to Gemini to produce contextual explanations with official source citations.

The calculator performs tax computations deterministically rather than relying on LLM-generated arithmetic.

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | Next.js, React, TypeScript, Tailwind CSS |
| Backend | Python, FastAPI, REST APIs |
| AI orchestration | Google Gemini API, function calling, custom agent execution loops |
| RAG | Gemini Embeddings, PostgreSQL, pgvector |
| Database | Neon PostgreSQL |
| Data ingestion | HTTPX, BeautifulSoup, Playwright |
| Data validation | Pydantic, JSON schemas |
| Testing | Pytest, calculator unit tests |
| Automation | GitHub Actions, scheduled workflows |
| Deployment | Vercel (frontend), Render (backend) |
| Version control | Git, GitHub |

## End-to-End Workflow

**Data ingestion:**

`GitHub Actions → Python Scrapers → Gemini Ingestion Agent → Verification Agent → Human Approval → Neon PostgreSQL`

Approved structured rules are stored for calculations, while relevant official documents are chunked, embedded, and indexed for semantic retrieval.

**User query processing:**

`Next.js → FastAPI → Gemini Assistant Agent → Tool Calling → RAG / Tax Calculator → PostgreSQL → Gemini → Frontend`

The frontend sends user queries to FastAPI through HTTP requests. FastAPI communicates with Gemini, executes requested Python tools, and returns the resulting explanations to the client.

## Design Principles

Ratios separates probabilistic AI reasoning from deterministic tax computation. AI agents handle information extraction, verification support, semantic retrieval, and tool orchestration, while Python functions execute calculations against approved, versioned tax rules. Human-in-the-loop verification, source attribution, automated testing, and scheduled data updates are incorporated to improve reliability and maintainability.

