# Support Ticket Router 🎫

> An intelligent, production-grade engine that automatically classifies, prioritizes, and routes customer support tickets — powered by a **Hybrid AI Engine** (Google Gemini + RegEx fallback) with a full microservices architecture.

Built as part of the **Software Development Internship** technical assessment at **Uruba Software**.

**Assessment scope:** the core submission is the CLI + rule engine (`python main.py`). FastAPI, Celery, Redis, PostgreSQL, Streamlit, Docker, webhooks, and AI integration are optional extensions demonstrating how the same core logic evolves into a production-grade service.

**🌐 Live Demo:** [https://support-ticket-router.streamlit.app/](https://support-ticket-router.streamlit.app/)

---

## 📋 Table of Contents

- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [AI Classification Engine](#ai-classification-engine)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Configuration (.env)](#configuration-env)
  - [Run Locally (CLI)](#run-locally-cli)
  - [Run with Docker (Full Stack)](#run-with-docker-full-stack)
  - [Run Streamlit UI](#run-streamlit-ui)
  - [Run Tests](#run-tests)
- [REST API Reference](#rest-api-reference)
- [Docker Services](#docker-services)
- [Classification Rules](#classification-rules)
- [Assessment Q&A](#assessment-qa)
- [Roadmap](#roadmap)

---

## Features

| Feature | Details |
|---|---|
| ✨ **Hybrid AI Engine** | Google Gemini 2.5 Flash Lite as primary classifier; automatic RegEx fallback when confidence is low or AI is unavailable |
| 🔌 **Multi-Provider AI** | Supports Gemini, HuggingFace API, local Transformers (offline), and Ollama — switchable via a single `.env` variable |
| 📊 **Confidence Scoring** | Every result includes a `confidence` score (0.0–1.0) and `aiUsed` flag |
| 🤖 **Scored Classification** | Categorizes tickets into `billing`, `account`, `technical`, or `general` using weighted keyword scoring |
| 🔥 **Priority Detection** | Assigns `high`, `medium`, or `low` based on customer tier and urgency keywords |
| 💬 **Dynamic Reasoning** | Explains classification decisions in natural language (AI) or rule-based detail (RegEx) |
| 🌐 **REST API (FastAPI)** | Async HTTP API with Swagger UI, Pydantic validation, and rate limiting |
| 📬 **Message Queues** | Celery + Redis for non-blocking asynchronous ticket processing |
| 🔔 **Webhook Notifications** | Sends rich Discord/Slack embeds when a ticket is assigned to a team |
| 🗄️ **Dual-Backend DB** | PostgreSQL in Docker/production; SQLite fallback for local/Streamlit Cloud |
| 🔒 **Secure Admin Panel** | Password-protected Streamlit dashboard for live rule management — no code changes needed |
| 📊 **Persistent History** | Processed tickets are stored in DB and survive page reloads |
| 🚦 **Rate Limiting** | `slowapi` protects the API endpoints (30 req/min for POST, 120/min for GET) |
| 📋 **Structured Logging** | Python `logging` module writes to `app.log` with timestamps |
| ✅ **72 Automated Tests** | Unit + E2E + AI test suites covering scoring, edge cases, fallback behaviour, and all 4 AI providers |
| 🐳 **Multi-Stage Docker** | Optimized container builds; each service carries only what it needs |

---

## Architecture Overview

```
                        ┌─────────────────────────────┐
                        │   Client / Web Form / cURL   │
                        └────────────┬────────────────┘
                                     │ POST /api/v1/process-ticket
                        ┌────────────▼────────────────┐
                        │   FastAPI REST API (:8000)  │
                        │   • Rate Limiting (slowapi) │
                        │   • Pydantic Validation     │
                        └────────────┬────────────────┘
                                     │ Enqueue Task
                        ┌────────────▼────────────────┐
                        │     Redis (Message Broker)  │
                        └────────────┬────────────────┘
                                     │ Dequeue Task
                        ┌────────────▼────────────────┐
                        │      Celery Worker           │
                        │   ┌──────────────────────┐  │
                        │   │  HybridClassifier    │  │
                        │   │  ┌────────────────┐  │  │
                        │   │  │  AI Provider   │  │  │  ← Gemini / HF / Ollama
                        │   │  └───────┬────────┘  │  │
                        │   │  confidence < 0.65?  │  │
                        │   │  ┌────────────────┐  │  │
                        │   │  │ TicketEvaluator│  │  │  ← RegEx fallback
                        │   │  └────────────────┘  │  │
                        │   │  TeamRouter           │  │
                        │   │  Notifier (Webhook)   │  │
                        │   └──────────────────────┘  │
                        │         │            │       │
                        │   PostgreSQL      Redis      │
                        │   (Rules DB +    (Result     │
                        │    History)       Backend)   │
                        └─────────────────────────────┘
                                     │
                        GET /api/v1/task/{task_id}
                        ← { status: "SUCCESS", result: {...} }
```

**Alternative Interfaces:**
- **Streamlit UI** (`app.py`) — Interactive dashboard with AI badge, confidence bar, and Admin Panel
- **CLI Batch Processor** (`main.py`) — Processes `data/tickets.json` directly

---

## AI Classification Engine

The system uses a **HybridClassifier** that puts AI first and falls back to the proven RegEx engine automatically.

```
Ticket Input
     │
     ▼
┌─────────────────────────────┐
│      HybridClassifier       │
│  ┌────────────────────────┐ │
│  │     AI Provider        │ │  ← Gemini / HuggingFace / Transformers / Ollama
│  └───────────┬────────────┘ │
│     confidence >= 0.65?     │
│              │ No           │
│              ▼              │
│  ┌────────────────────────┐ │
│  │   RegEx Engine         │ │  ← TicketEvaluator (unchanged, deterministic)
│  └────────────────────────┘ │
└─────────────────────────────┘
     │
     ▼
ProcessedTicket { category, priority, assignedTeam, reason, confidence, aiUsed }
```

### Supported AI Providers

| Provider | Setup | Internet | Speed | Set in `.env` |
|---|---|---|---|---|
| **Google Gemini 2.5 Flash Lite** ⭐ | `pip install google-genai` | Required | Fast | `AI_PROVIDER=gemini` |
| **HuggingFace Inference API** | `pip install huggingface_hub` | Required | Medium | `AI_PROVIDER=huggingface` |
| **Local Transformers (offline)** | `pip install transformers torch` | First run only | Slow (CPU) | `AI_PROVIDER=transformers` |
| **Ollama (local LLM)** | [ollama.com](https://ollama.com) + `ollama pull phi4-mini` | No | Medium | `AI_PROVIDER=ollama` |
| **RegEx only** | — | No | Instant | `AI_PROVIDER=none` |

Switch providers without touching any code — just change `AI_PROVIDER` in `.env`.

### Confidence Threshold

When AI confidence drops below `AI_CONFIDENCE_THRESHOLD` (default: `0.65`), the system silently falls back to the RegEx engine. The result is identical from the caller's perspective — only `aiUsed: false` indicates which path ran.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **AI Classification** | Google Gemini 2.5 Flash Lite (primary), HuggingFace, Transformers, Ollama |
| **API Framework** | FastAPI + Uvicorn |
| **Async Processing** | Celery + Redis |
| **Database (Prod)** | PostgreSQL 16 |
| **Database (Dev)** | SQLite (auto-fallback) |
| **Web UI** | Streamlit |
| **Config** | `config/settings.py` + `.env` |
| **Rate Limiting** | slowapi |
| **Notifications** | Discord/Slack Webhooks via `requests` |
| **Testing** | pytest (72 tests: Unit + E2E + AI) |
| **Containerization** | Docker + Docker Compose (5 services) |

---

## Project Structure

```
support-ticket-router/
│
├── api.py                    # FastAPI REST API entry point
├── worker.py                 # Celery async background worker (AI-enabled)
├── main.py                   # CLI batch processor (main assessment deliverable)
├── app.py                    # Streamlit UI + Admin Panel + AI badge
│
├── config/
│   └── settings.py           # ✨ Central config — all env vars in one place
│
├── database/
│   └── db.py                 # Dual-backend DB (PostgreSQL + SQLite fallback)
│
├── engine/
│   ├── evaluator.py          # Scored classification engine (RegEx + tie-break rules)
│   ├── router.py             # Team routing engine
│   ├── notifier.py           # Discord/Slack webhook dispatcher
│   ├── ai_classifier.py      # ✨ HybridClassifier (AI-first + RegEx fallback)
│   └── providers/            # ✨ Pluggable AI provider modules
│       ├── __init__.py       #    BaseAIProvider abstract class
│       ├── gemini_provider.py
│       ├── huggingface_provider.py
│       ├── transformers_provider.py
│       └── ollama_provider.py
│
├── models/
│   └── ticket.py             # Typed dataclasses (Ticket, ProcessedTicket)
│
├── tests/
│   ├── test_evaluator.py     # 27 unit tests (RegEx engine)
│   ├── test_e2e.py           # 15 E2E pipeline tests
│   └── test_ai_classifier.py # ✨ 30 AI tests (HybridClassifier + all providers)
│
├── data/
│   └── tickets.json          # Sample input (assessment data)
│
├── assets/
│   └── styles.css            # 🎨 Custom CSS — premium dark-mode UI theme
│
├── .streamlit/
│   └── config.toml           # Streamlit theme config (dark mode, brand colors)
│
├── docker-compose.yml        # 5-service orchestration
├── Dockerfile                # Multi-stage build
├── requirements.txt
├── .env.example              # Configuration template
└── README.md
```

---

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (recommended)
- OR Python 3.11+ for local development
- A free [Google AI Studio](https://aistudio.google.com) API key (optional — system works without it)

### Configuration (.env)

```bash
cp .env.example .env
```

> [!IMPORTANT]
> **Zero-config for local use.** The `.env` file works as-is for local and Streamlit Cloud runs.
> Docker Compose automatically overrides `DATABASE_URL` and `REDIS_URL` for its own containers — you never need to edit these manually.

Key settings in `.env`:

```env
# PostgreSQL credentials (Docker uses these to create the DB)
POSTGRES_USER=admin
POSTGRES_PASSWORD=secret123
POSTGRES_DB=ticket_db

# Leave empty — SQLite is used locally; Docker sets this automatically
DATABASE_URL=

# Leave as localhost — Docker overrides to redis://redis:6379/0 internally
REDIS_URL=redis://localhost:6379/0

# ── AI Configuration ──────────────────────────────────
# Options: gemini | huggingface | transformers | ollama | none
AI_PROVIDER=gemini

# Google Gemini (free at aistudio.google.com)
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash-lite

# Confidence threshold — below this, RegEx engine takes over
AI_CONFIDENCE_THRESHOLD=0.65
```

**Environment summary — same `.env` file works everywhere:**

| Environment | Database | Redis | Command |
|---|---|---|---|
| **Local CLI** | SQLite (auto) | Not needed | `python main.py` |
| **Local Streamlit** | SQLite (auto) | Not needed | `streamlit run app.py` |
| **Local Tests** | SQLite (temp) | Not needed | `pytest tests/` |
| **Docker** | PostgreSQL (auto) | Docker Redis (auto) | `docker compose up` |
| **Streamlit Cloud** | SQLite (auto) | Not needed | Deployed automatically |

> **Security Note:** `.env` is git-ignored. Never commit real secrets to source control.

---

### Run Locally (CLI)

The core assessment deliverable — processes `data/tickets.json` and outputs results:

```bash
pip install -r requirements.txt
python main.py
```

Output is printed to console and saved to `data/processed_tickets.json`.

With AI enabled, each ticket shows:
```json
{
  "id": 1,
  "category": "billing",
  "priority": "high",
  "assignedTeam": "payments-team",
  "reason": "The ticket is about a failed payment with money withdrawn, indicating a billing issue. Premium customer elevates priority to high.",
  "confidence": 0.95,
  "aiUsed": true
}
```

---

### Run with Docker (Full Stack)

```bash
docker compose up --build
```

Services start in dependency order (DB and Redis first, then API and Worker).

> [!NOTE]
> The `ticket-router-cli` service is a **run-once job**. See its output with `docker compose logs ticket-router-cli`.

---

### Run Streamlit UI

```bash
streamlit run app.py
```

Or visit the live hosted version: 👉 **[https://support-ticket-router.streamlit.app/](https://support-ticket-router.streamlit.app/)**

The UI shows:
- **`✨ AI · gemini-2.5-flash-lite`** badge when Gemini classifies the ticket
- **Confidence bar** showing the AI's certainty percentage
- **`⚙️ RegEx Engine`** badge when the fallback is used

**Admin Panel Access:**
1. Open left sidebar → click **Admin Panel**
2. Enter password: `admin123`
3. Add / edit / delete categories and keywords — changes take effect immediately

---

### Run Tests

```bash
pytest tests/ -v
```

**Expected output:** `72 passed`

| Test Suite | Count | Coverage |
|---|---|---|
| `test_evaluator.py` | 27 | Category scoring, tie-breaks, detail analysis, reason generation, priority rules |
| `test_e2e.py` | 15 | All 4 case tickets, empty list, None fields, malformed data, output format |
| `test_ai_classifier.py` | 30 | HybridClassifier (AI path, fallback, threshold), Ollama provider, Transformers provider, ProcessedTicket fields, BaseAIProvider contract |

---

## REST API Reference

Base URL: `http://localhost:8000`

Interactive docs: **[http://localhost:8000/docs](http://localhost:8000/docs)** (Swagger UI)

### `POST /api/v1/process-ticket`

Enqueues a ticket for async AI classification. Returns a `task_id` immediately.

**Rate Limit:** 30 requests/minute per IP

**Request Body:**
```json
{
  "id": 1001,
  "subject": "Urgent refund request",
  "message": "My payment was charged twice, this looks like fraud!",
  "customerType": "premium",
  "createdAt": "2026-05-05T10:00:00Z"
}
```

**Response `200`:**
```json
{
  "task_id": "8b52df3e-7a45-4d2f-9c11-abc123def456",
  "status": "PENDING",
  "result": null
}
```

---

### `GET /api/v1/task/{task_id}`

Polls the status and result of a previously submitted ticket.

**Rate Limit:** 120 requests/minute per IP

**Response (when complete):**
```json
{
  "task_id": "8b52df3e-...",
  "status": "SUCCESS",
  "result": {
    "id": 1001,
    "category": "billing",
    "priority": "high",
    "assignedTeam": "payments-team",
    "reason": "The customer is reporting a double charge, which is a billing issue. The customer is premium and the issue involves potential fraud, making the priority high.",
    "confidence": 0.95,
    "aiUsed": true
  }
}
```

---

### `GET /health`

Simple liveness probe.

```json
{ "status": "ok", "version": "1.0.0" }
```

---

## Docker Services

| Service | Image | Port | Role |
|---|---|---|---|
| `db` | `postgres:16-alpine` | 5432 | PostgreSQL database (rules + history) |
| `redis` | `redis:alpine` | 6379 | Celery broker & result backend |
| `ticket-router-api` | Local build | **8000** | FastAPI REST API |
| `celery-worker` | Local build | — | Background ticket processor (AI-enabled) |
| `ticket-router-cli` | Local build | — | Batch JSON processor |

All services use `healthcheck` to ensure correct startup ordering.
PostgreSQL data is persisted via a named Docker Volume (`postgres_data`).

---

## Classification Rules

### Category Rules

| Category | Keywords | Team |
|---|---|---|
| `billing` | billing, payment, invoice, refund, money, card, charge, paid, withdrawn | `payments-team` |
| `account` | login, password, account, access, authentication | `account-support` |
| `technical` | crash, bug, error, broken, loading, upload, not working | `technical-support` |
| `general` | *(no keyword match)* | `general-support` |

### Category Scoring (RegEx Engine)

When the RegEx engine runs (AI unavailable or low confidence), it uses weighted scoring:

| Match Location | Score |
|---|---:|
| Keyword match in `subject` | `+2` |
| Keyword match in `message` | `+1` |

Tie-break order:
1. Highest total score wins
2. If tied, more subject matches wins
3. If still tied: `billing > technical > account > general`

### Priority Rules

| Priority | Conditions |
|---|---|
| **High** | Customer type is `premium` **OR** urgency keywords (`urgent`, `asap`, `blocked`, ...) **OR** billing ticket with financial terms (`money`, `refund`, `withdrawn`, `fraud`, ...) |
| **Medium** | Category is `technical` or `account` |
| **Low** | All other cases |

> All rules are stored in the database and can be modified live via the Admin Panel — **no code changes required**.

---

## Assessment Q&A

### Why implement AI, Docker, REST API, and Celery if they weren't requested?

The email stated: *"The goal of this task is not only to assess technical ability, but also to better understand your problem-solving approach, code structure, and decision-making process."* 

While a simple `if/else` script satisfies the baseline requirements, it doesn't reflect how real-world software is built. I wanted to demonstrate my ability to design **production-grade, scalable architectures**:

1. **Hybrid AI Engine:** Shows how to integrate LLMs (Gemini/HuggingFace) gracefully while maintaining a deterministic fallback (RegEx) for reliability and safety.
2. **FastAPI & Celery:** Demonstrates asynchronous processing. In the real world, AI processing takes seconds; blocking a REST API for it is poor design. Celery decouples the workload.
3. **Docker & PostgreSQL:** Shows DevOps awareness. The app is ready to deploy anywhere via containers.
4. **Clean Architecture:** By decoupling the core engine (`HybridClassifier`) from the entry points, the exact same logic runs seamlessly in a CLI batch job, a REST API worker, and a Streamlit UI.

### How did you break down the problem?

I adopted a highly modular, decoupled approach inspired by **Clean Architecture** principles:

1. **Data Models** (`models/ticket.py`) — Strictly typed `dataclass` schemas with AI metadata fields (`confidence`, `ai_used`)
2. **Config** (`config/settings.py`) — Single source of truth for all env variables including AI provider settings
3. **Database Layer** (`database/db.py`) — Dual-backend (PostgreSQL/SQLite) with automatic fallback
4. **Core Engines** (`engine/`) — Stateless, testable classes; `HybridClassifier` wraps the existing `TicketEvaluator` without modifying it
5. **AI Provider Abstraction** (`engine/providers/`) — `BaseAIProvider` interface enables adding new AI backends without touching any existing code
6. **Async Layer** (`worker.py`, `api.py`) — Celery + Redis decouple request intake from AI processing
7. **Interfaces** (`app.py`, `main.py`) — All three entry points (CLI, Streamlit, REST API) use the same `HybridClassifier`

### What assumptions did you make?

- Case insensitivity is required ("ReFunD" must match "refund")
- Tickets may have `None` or empty fields — all handled gracefully
- AI results with confidence below threshold should silently fall back (no error to caller)
- API key security: `.env` is git-ignored; API keys never reach source control
- JSON API uses `camelCase` externally; Python internals use `snake_case` (PEP 8)

### What edge cases did you handle?

- ✅ `None` / empty fields default to `general` / `low`
- ✅ Multi-category tickets use weighted scoring instead of first-match routing
- ✅ Score ties are deterministic
- ✅ False-positive substrings (`non-refundable` matching `refund`) — blocked via `\b` word boundaries
- ✅ AI provider down / rate-limited → silent RegEx fallback, no crash
- ✅ AI returns low-confidence result → RegEx takes over transparently
- ✅ `google-genai` package missing → ImportError caught, RegEx used
- ✅ Invalid ticket entries in a batch are skipped with a `WARNING` log
- ✅ Empty ticket lists produce an empty output without errors
- ⚠️ Negation context ("I do NOT want a refund") — not handled; requires NLP

### How can I test the code?

```bash
pip install -r requirements.txt
python main.py        # CLI with AI (or RegEx if AI_PROVIDER=none)
pytest tests/ -v      # Should report 72 passed
streamlit run app.py  # UI with AI badge
```

### What would you change first if requirements evolved?

1. **Fine-tuned model** — Replace zero-shot with a domain-fine-tuned model on historical ticket data for higher confidence scores
2. **Streaming responses** — Add SSE/WebSocket support to the FastAPI layer for real-time classification progress
3. **Multi-Tenant Auth** — Replace the single admin password with OAuth2/JWT for multi-user management

---

## Roadmap

| Phase | Status | Description |
|---|---|---|
| Phase 1 | ✅ | Core engine: classification, priority, routing, JSON I/O |
| Phase 2 | ✅ | RegEx matching, E2E tests, structured logging |
| Phase 3 | ✅ | SQLite → PostgreSQL (dual-backend), Streamlit Admin Panel |
| Phase 4 | ✅ | FastAPI REST API, Celery + Redis async queues |
| Phase 5 | ✅ | Discord Webhooks, Docker Compose (5 services), multi-stage builds |
| Phase 6 | ✅ | Central config, rate limiting, ticket history persistence, 42-test suite |
| Phase 7 | ✅ | Premium UI modernization (dark mode, glassmorphism, particle animations) |
| Phase 8 | ✅ | **Hybrid AI Engine** — Gemini, HuggingFace, Transformers, Ollama; 72-test suite |
| Phase 9 | 🔜 | Fine-tuned domain model + streaming API responses |
