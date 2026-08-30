Cadence - AI Calendar Assistant
# Cadence — AI Calendar Assistant

An AI agent that manages your Google Calendar through natural conversation: view, create, reschedule, cancel and search meetings, set custom reminders, work across multiple calendars, and pull context from your own uploaded work documents (PDF/DOCX/TXT) to schedule accordingly.

## Stack
- **Backend**: FastAPI, LangGraph (tool-calling agent + Postgres-backed short/long-term memory), Groq (free LLM inference, `openai/gpt-oss-120b`)
- **Frontend**: Next.js, Tailwind, Descope (auth + Google Calendar OAuth)
- **Storage**: Postgres + pgvector (chat checkpoints, long-term memory facts, document embeddings)
- **RAG**: fastembed (local, free embeddings) + pgvector similarity search, scoped to work-relevant documents only via an LLM classifier gate
- **Evals**: DeepEval (GEval for open-ended behavior) + RAGAS (retrieval faithfulness/precision) + deterministic classifier tests, all Groq-judged — zero paid API calls anywhere in the stack
- **Observability**: LangSmith tracing

## Features
- Natural-language calendar CRUD: view, create, reschedule, cancel, recurring events (RRULE), custom reminders
- Resolves meetings by name/topic, no manual event IDs needed
- Multi-calendar support (pick which calendars the agent reads/writes)
- Document-aware scheduling: upload a PDF/DOCX/TXT (agenda, sprint plan, meeting notes); rejected if it's not work-relevant
- Entity/document disambiguation (won't guess between two "Johns" or two uploaded files)
- Short-term memory (full conversation history, survives backend restarts) + long-term memory (facts persist across threads)
- Strict scope guardrail (refuses off-topic requests) with no leakage of internal tool/model/framework names
- Dark/light theme, responsive layout, collapsible sidebar, thread management with delete confirmation

## Setup
1. `docker compose up -d` — starts Postgres
2. Backend: `cd backend && python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt && python scripts\migrate.py && python run.py`
3. Frontend: `cd frontend && npm install && npm run dev`
4. Configure `backend/.env` and `frontend/.env` (see `.env.example` in each) — Descope project ID/management key, Groq API key, Postgres URL
5. In Descope Console, set up a Google Calendar Outbound App with your Google OAuth client (scope: `https://www.googleapis.com/auth/calendar`)

## Testing