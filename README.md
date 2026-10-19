# Taxly: Your AI Copilot for Canadian Tax Planning 🇨🇦

Currently in progress …

Taxora is a full-stack, Agentic AI-powered Canadian tax platform designed to help users understand, calculate, and optimize their federal and provincial income taxes through natural-language conversations. Built using Next.js, React, TypeScript, Python, FastAPI, LangChain, Google Gemini, and Neon PostgreSQL, Ratios uses an intelligent AI agent that selects and executes specialized Python tools for income tax calculations, RRSP and TFSA analysis, capital gains, payroll deductions, and tax scenario comparisons. 

The system also incorporates Retrieval-Augmented Generation (RAG), using vector embeddings and PostgreSQL's pgvector extension to retrieve relevant information from official Canadian tax documents and generate answers supported by reliable sources. 

Rather than relying on AI-generated calculations, TaxPilot uses deterministic Python functions and verified government tax rules to ensure numerical accuracy. The architecture also includes automated data ingestion and verification agents designed to collect, validate, and maintain up-to-date tax information, with human approval before new rules enter production. By combining agentic AI, RAG, reliable tax calculations, and source verification, Ratios aims to make Canadian taxation more accessible, transparent, and easier to understand.

## System Architecture

TaxPilot is organized into three AI agents and a deterministic Python tax engine.

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
| Data ingestion | HTTPX, BeautifulSoup, Selenium, Playwright |
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

TaxPilot separates probabilistic AI reasoning from deterministic tax computation. AI agents handle information extraction, verification support, semantic retrieval, and tool orchestration, while Python functions execute calculations against approved, versioned tax rules. Human-in-the-loop verification, source attribution, automated testing, and scheduled data updates are incorporated to improve reliability and maintainability.

