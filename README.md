# Ratios: Agentic AI Canadian Tax Assistant

Ratios is an agentic AI-powered Canadian income tax assistant designed to help users understand tax regulations, calculate income taxes, and explore tax-saving scenarios through natural language. The system combines AI agents, retrieval-augmented generation (RAG), and a deterministic Python tax calculator to provide accurate, explainable answers grounded in official Canadian government sources.

## System Design

Ratios consists of two main workflows:

1. **Tax Rule Ingestion:** AI agents periodically collect tax information from official CRA and provincial government sources, extract structured tax rules, and cross-check their accuracy. Proposed updates undergo human approval before being stored in the production database.
2. **User Assistant:** A tool-calling AI agent interprets user questions and dynamically selects between RAG-based document retrieval, tax calculations, and scenario comparisons. RAG retrieves relevant government documentation, while the Python calculator performs calculations using verified tax rules.

## Tech Stack

- **Frontend:** Next.js, React, TypeScript, Tailwind CSS
- **Backend:** Python, FastAPI, REST APIs
- **AI & Agents:** Google Gemini, tool/function calling, agentic workflows
- **RAG:** Gemini Embeddings, PostgreSQL with pgvector
- **Database:** Neon PostgreSQL
- **Data Extraction:** BeautifulSoup, HTTPX, Playwright
- **Validation & Testing:** Pydantic, Pytest
- **Automation:** GitHub Actions
- **Deployment:** Vercel (frontend), Render (backend)

**Architecture:** Next.js → FastAPI → Gemini Agent → RAG / Python Tax Calculator → PostgreSQL → AI-generated response.
