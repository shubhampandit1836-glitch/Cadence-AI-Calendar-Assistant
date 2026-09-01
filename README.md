# Cadence — AI Calendar Assistant

Cadence is an agentic, full-stack calendar assistant that manages your Google Calendar through natural conversation. It combines a LangGraph ReAct agent, thread-aware Retrieval-Augmented Generation over your uploaded documents, and a Model Context Protocol (MCP) server — all backed by a Postgres/pgvector persistence layer and validated by a three-tier automated evaluation suite.

Built as a demonstration of production AI-engineering practices: agent orchestration, RAG pipelines, LLM evaluation, observability, and safe tool-calling design — not just a calendar CRUD wrapper with a chat UI on top.

---

## Table of Contents

- [What it does](#what-it-does)
- [Architecture](#architecture)
- [Why this is more than a calendar bot](#why-this-is-more-than-a-calendar-bot)
- [Tech stack](#tech-stack)
- [Evaluation suite](#evaluation-suite)
- [Safety & reliability patterns](#safety--reliability-patterns)
- [Getting started](#getting-started)
- [Running with Docker](#running-with-docker)
- [Running tests](#running-tests)
- [CI/CD](#cicd)
- [MCP server](#mcp-server)
- [Project structure](#project-structure)
- [Known limitations](#known-limitations)
- [Roadmap](#roadmap)

---

## What it does

Talk to Cadence the way you'd talk to an assistant, and it handles your calendar:

- **"Am I free tomorrow between 2 and 4?"** — checks free/busy across every calendar you've selected, not just your primary.
- **"Create a recurring standup every Monday at 10am for 8 weeks"** — creates a properly bounded recurring series (never open-ended by accident).
- **"Cancel the Test Sync series"** — cancels the entire recurring series in one call by targeting the master event, not by deleting hundreds of individual occurrences one at a time.
- **Upload a PDF** and ask "what's in this?" — Cadence chunks, embeds, and indexes the document, then answers grounded in the actual retrieved content (verified faithful via automated RAGAS evaluation).
- **"Schedule a follow-up with John Carter"** when two Johns exist in an uploaded doc — Cadence disambiguates rather than guessing, and remembers which one you meant within the thread.
- Ask something off-topic ("what's the weather?") — Cadence politely declines and redirects, without ever exposing its internal tool names or underlying model/provider.

---

## Architecture

```
┌─────────────────┐         ┌──────────────────────────────────────────────┐
│   Next.js UI     │  HTTPS  │                FastAPI Backend                │
│  (React, SSE)    │────────▶│                                                │
└─────────────────┘         │  ┌──────────────┐    ┌────────────────────┐  │
                             │  │  Supervisor   │    │   LangGraph ReAct   │  │
                             │  │  Classifier   │───▶│       Agent         │  │
                             │  │ (scope gate)  │    │  (Groq LLM + tools) │  │
                             │  └──────────────┘    └──────────┬─────────┘  │
                             │                                  │            │
                             │        ┌─────────────────────────┼──────┐     │
                             │        ▼                         ▼      ▼     │
                             │  ┌───────────┐          ┌──────────┐ ┌─────┐ │
                             │  │  Google    │          │   RAG     │ │ MCP │ │
                             │  │  Calendar  │          │ Pipeline  │ │Tools│ │
                             │  │    API     │          │(pgvector) │ │     │ │
                             │  └───────────┘          └──────────┘ └─────┘ │
                             │                                                │
                             │  ┌──────────────────────────────────────────┐ │
                             │  │  Postgres (threads, memory, docs, chunks, │ │
                             │  │  checkpoints) — LangGraph checkpointer     │ │
                             │  │  provides per-thread conversational state  │ │
                             │  └──────────────────────────────────────────┘ │
                             └──────────────────────────────────────────────┘
                                          │
                                          ▼
                             ┌──────────────────────────┐
                             │   Descope (outbound OAuth) │
                             │   → Google Calendar API    │
                             └──────────────────────────┘
```

**Request flow for a chat message:**

1. Message hits `/api/agent/chat`, rate-limited per-route (slowapi).
2. A lightweight **supervisor classifier** call decides in/out of scope before the main agent ever runs — off-topic requests get redirected without spending a full agent turn.
3. The **LangGraph ReAct agent** runs with the user's calendar tools, RAG search tool, and conversational memory injected into its system prompt.
4. Tool calls (Google Calendar API, document search) execute; results feed back into the agent loop.
5. The reply streams back over Server-Sent Events.
6. In the background (fire-and-forget, not blocking the reply): the turn is checked for a durable, reusable fact worth storing in long-term memory — explicitly excluding anything event-specific, since calendar events can be edited or cancelled and would go stale.

---

## Why this is more than a calendar bot

This project was deliberately built to exercise the parts of AI engineering that don't show up in a typical CRUD-with-a-chatbot project:

- **Thread-aware RAG with document lifecycle management** — documents are scoped per-user and per-conversation, chunked, embedded via FastEmbed, stored in pgvector, and re-indexed cleanly on re-upload (old chunks are cascade-deleted, not orphaned).
- **A real three-tier evaluation suite**, not just manual spot-checks (see below) — behavioral evals (GEval), retrieval evals (RAGAS faithfulness/precision), and deterministic unit tests, all wired into CI.
- **Safe, idempotent tool design** — cancelling a recurring meeting targets the series' master event rather than looping over occurrences, both for performance and correctness (an unbounded weekly series can never be "caught up with" by deleting instances one at a time — the fix here was diagnosed and shipped as a genuine correctness bug, not just an optimization).
- **Identity and referential integrity** — foreign keys tie every user-scoped table back to `users`, added via a migration that safely handles pre-existing orphaned rows rather than assuming a clean slate.
- **An MCP server**, not just an in-app agent — the same calendar tools are exposed over the Model Context Protocol so external MCP clients (Claude Desktop, Cursor, etc.) can use them, authenticated via the same Descope session as the web app — no separate/hardcoded identity path.
- **Deliberate identity and tool-name protection** — the agent is instructed and evaluated (via `identity_protection` and `tool_name_protection` GEval cases) to never leak its underlying model, provider, or internal function names to the end user.

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js, React, Server-Sent Events for streaming |
| Backend | FastAPI, Python 3.11 |
| Agent orchestration | LangGraph (ReAct agent pattern) |
| LLM | Groq (configurable via `MODEL_PROVIDER`/`MODEL_NAME`) |
| Auth | Descope (session auth + outbound OAuth to Google) |
| Database | PostgreSQL 16 + pgvector extension |
| Vector embeddings | FastEmbed |
| Document parsing | pypdf, python-docx |
| Eval framework | DeepEval (GEval behavioral metrics), RAGAS (retrieval metrics) |
| Rate limiting | slowapi |
| CI | GitHub Actions |
| Containerization | Docker, Docker Compose |
| External protocol | MCP (Model Context Protocol) server |

---

## Evaluation suite

Cadence ships with a genuine three-tier automated evaluation suite — 60 tests total, wired into CI on every PR.

### 1. Deterministic unit tests (mocked, no external services)
Fast, hermetic tests that pin known-fixed bugs so they can never regress silently:
- `test_calendar_service_unit.py` — pins multi-calendar `check_calendar_busy` behavior (regression guard against the old "always queries primary" bug).
- `test_document_repository_unit.py` — pins `delete_all_documents` return-value correctness after dead-code cleanup.

### 2. Behavioral evaluation (DeepEval GEval, LLM-as-judge)
`test_agent_behavior_geval.py` scores the agent's actual conversational behavior against natural-language requirements, covering:
- Entity disambiguation (ambiguous vs. already-resolved names)
- Document disambiguation across multiple attached files
- Retroactive execution of a previously-blocked request once required info arrives
- Graceful handling of blank/empty document content
- Off-topic refusal tone
- **Identity protection** — never reveals the underlying model/provider
- **Tool-name protection** — describes capabilities in plain language, never leaks internal function names

`test_supervisor_eval.py` and `test_document_classifier_eval.py` similarly validate the scope-classification and document-relevance classification steps against dozens of in/out-of-scope and relevant/irrelevant examples.

### 3. Retrieval quality (RAGAS)
`test_rag_retrieval_eval.py` runs real RAG queries against seeded documents and scores **faithfulness** (are answers grounded in retrieved context, not hallucinated?) and **context precision** (did retrieval actually surface the relevant chunks?) using an LLM-as-judge, with a `0.7` minimum threshold on both.

Run the full suite:

```bash
docker-compose exec backend pytest -v
```

Run just the fast, free unit tests:

```bash
docker-compose exec backend pytest tests/test_calendar_service_unit.py tests/test_document_repository_unit.py -v
```

> **Note on rate limits:** the eval suite makes real LLM calls. On Groq's free/on-demand tier, running the full suite back-to-back with heavy manual testing can hit per-minute or per-day token caps, surfacing as `429`/`RateLimitError` rather than a real behavioral failure. Check the captured test output for `rate_limit_exceeded` before treating a failure as a regression — isolated re-runs of a rate-limited test reliably pass once quota clears.

---

## Safety & reliability patterns

A few patterns worth calling out explicitly, since they were the source of real bugs found and fixed during hardening:

- **Permanent vs. transient error handling in repositories** — database writes only reset the shared connection pool on genuinely transient failures (dropped connections). Integrity violations (e.g. a foreign-key constraint failure) are permanent and are raised immediately instead — resetting the pool on a permanent error would otherwise tear down connections mid-flight for every other concurrent request sharing that pool.
- **Non-blocking bulk operations** — any tool that makes many sequential external API calls (e.g. cancelling all upcoming meetings) runs on a worker thread (`asyncio.to_thread`), so it can never freeze the single-process event loop for every other user's request.
- **Recurring series are cancelled at the series level** — via the master event's `recurringEventId`, not by paging through individual occurrences, which is both correct (an unbounded series can otherwise never be "cancelled" this way) and dramatically faster.
- **Classifier-model input truncation** — any text passed into the low-token-budget classifier model (used for scope-checking and memory extraction) is truncated first, preventing oversized tool outputs (e.g. a 60-day schedule table) from blowing the model's per-minute token cap.
- **Fire-and-forget memory extraction** — long-term memory extraction runs as a background task rather than being awaited before the reply completes, so it never adds latency to the user-facing response.
- **FK-enforced referential integrity** — every user-scoped table (`threads`, `user_memory`, `user_documents`, `document_chunks`, `calendar_preferences`) has a foreign key back to `users` with cascading deletes, applied via a migration that first removes any pre-existing orphaned rows so it can be run safely against a live database.

---

## Getting started

### Prerequisites
- Docker & Docker Compose
- A Google Cloud project with the Calendar API enabled
- A Descope project (for auth + outbound OAuth to Google)
- A Groq API key

### Environment setup

You'll need three `.env` files:

```bash
cp backend/.env.example backend/.env         # fill in DATABASE_URL, GROQ_API_KEY, DESCOPE_*, etc.
cp frontend/.env.example frontend/.env.local # fill in NEXT_PUBLIC_API_URL, NEXT_PUBLIC_DESCOPE_PROJECT_ID
cp .env.example .env                          # root .env, used by docker-compose for build-arg substitution
```

### Local development (without Docker)

```bash
# 1. Start Postgres only
docker-compose up -d agentic_calendar_db

# 2. Backend
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python scripts/migrate.py
python run.py                   # → http://localhost:4000

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev                     # → http://localhost:3000
```

---

## Running with Docker

The full stack — Postgres, backend, and frontend — runs via Docker Compose:

```bash
docker-compose up --build
```

| Service | Port |
|---|---|
| Frontend | `http://localhost:3000` |
| Backend | `http://localhost:4000` |
| Postgres | `localhost:5433` |

Health check:

```bash
curl http://localhost:4000/health
# {"status":"ok","database":"connected"}
```

---

## Running tests

```bash
# Full suite (60 tests: unit + behavioral evals + retrieval evals)
docker-compose exec backend pytest -v

# Unit tests only (fast, no external calls)
docker-compose exec backend pytest tests/test_calendar_service_unit.py tests/test_document_repository_unit.py -v

# Seed eval fixtures (required before running the eval suite fresh)
docker-compose exec backend python -m tests.seed_eval_user
docker-compose exec backend python -m tests.seed_eval_documents
```

---

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`) runs on every push/PR to `main`:

1. **`backend-unit-tests`** — mocked unit tests, no external services required.
2. **`backend-eval-suite`** — spins up a real pgvector Postgres service container, runs migrations, seeds eval fixtures, and runs the full DeepEval/RAGAS suite. Skips cleanly if `GROQ_API_KEY` isn't configured as a repo secret, so the pipeline never fails on missing credentials — it just skips the LLM-dependent job.

---

## MCP server

Cadence exposes its calendar tools over the [Model Context Protocol](https://modelcontextprotocol.io), so external MCP clients (Claude Desktop, Cursor, etc.) can use the same tools as the in-app agent — authenticated via the same Descope session, never a hardcoded identity.

```bash
# Public capability manifest (no auth required)
curl http://localhost:4000/mcp

# Tool calls require a valid Descope session bearer token
curl -X POST http://localhost:4000/mcp/messages \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <session-token>" \
  -d '{"method": "tools/list"}'
```

Exposed tools: `list_upcoming_meetings`, `check_calendar_busy`, `find_meeting_by_title`.

---

## Project structure

```
backend/
├── src/
│   ├── config/           # DB pool, rate limiter, LLM/classifier model config, agent instructions
│   ├── mcp/               # MCP server mount + tool definitions
│   ├── middleware/         # Session auth
│   ├── repositories/        # DB access layer (threads, documents, memory)
│   ├── routes/             # FastAPI routers (agent, documents, calendars, connections)
│   └── services/            # Business logic (calendar, RAG, agent orchestration, agent tools)
├── sql/                   # Versioned migrations
├── tests/
│   ├── test_*_unit.py           # Deterministic unit tests (mocked)
│   ├── test_agent_behavior_geval.py   # Behavioral evals (DeepEval GEval)
│   ├── test_rag_retrieval_eval.py     # Retrieval quality evals (RAGAS)
│   ├── test_supervisor_eval.py         # Scope-classifier evals
│   ├── test_document_classifier_eval.py # Document-relevance classifier evals
│   ├── seed_eval_user.py                # Idempotent eval fixture seeding
│   └── seed_eval_documents.py
├── Dockerfile
└── requirements.txt

frontend/
├── app/ or pages/         # Next.js routes
├── components/            # UI components (chat, sidebar, connection panel)
├── Dockerfile
└── next.config.mjs

.github/workflows/ci.yml   # CI pipeline
docker-compose.yml          # Full-stack orchestration
```

---

## Known limitations

Documented deliberately, rather than hidden — an accurate account of trade-offs is more useful to a reviewer than a project that claims to have none:

- **Attachment metadata is a parsed text convention**, not structured metadata — attachments are threaded through chat as a `[Attached: file.pdf]` suffix on the message string, regex-parsed on the way in. Functional, but a structured schema would be more robust; changing it touches the chat schema and streaming protocol and needs its own test pass.
- **Dual identity keys by design, not renamed** — `oauth_user_id` (Descope subject, used by agent/tool-written tables) and `users.id` (internal UUID, used by tables that model a relationship to the user row itself) coexist. Both are now foreign-key-enforced, but a full rename to a single canonical key was deemed too invasive to do without dedicated regression testing.
- **Groq free/on-demand tier rate limits** — the classifier model has an 8,000 token/minute and 200,000 token/day cap on the free tier, which the eval suite and heavy manual testing can exhaust. This affects local dev/testing throughput, not runtime correctness.

## Roadmap

- [ ] Structured attachment metadata (replace the `[Attached: ...]` text convention)
- [ ] Full identity-key normalization across all tables
- [ ] Sentry integration for production error tracking
- [ ] Live deployed demo link
- [ ] Architecture diagram + short demo GIF embedded above

---

## Deployment

This project is deployed as a single Docker container on Render's free tier — Postgres, the FastAPI backend, and the Next.js frontend all run together in one service, managed by `supervisord`, behind one shared URL.

**Why single-container:** one free link, zero cost, no need to coordinate multiple providers or environment variables across separate services.

**Trade-off:** Render's free tier uses ephemeral disk, so the database resets on every sleep/wake cycle (the service sleeps after 15 minutes of inactivity). This is acceptable for a shareable demo but means data doesn't persist long-term — worth knowing if you're testing features that depend on saved state across sessions.

See `Dockerfile.all-in-one`, `deploy/start.sh`, and `deploy/supervisord.conf` for the full container setup — Postgres initializes and runs migrations on every cold start, then `supervisord` brings up the backend and frontend together.

## License

MIT
