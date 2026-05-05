# Support Ticket Router 🎫

> An intelligent, production-grade engine that automatically classifies, prioritizes, and routes customer support tickets using rule-based logic and a full microservices architecture.

Built as part of the **Software Development Internship** technical assessment at **Uruba Software**.

**🌐 Live Demo:** [https://support-ticket-router.streamlit.app/](https://support-ticket-router.streamlit.app/)

---

## 📋 Table of Contents

- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Configuration (.env)](#configuration-env)
  - [Run with Docker (Recommended)](#run-with-docker-recommended)
  - [Run Locally (CLI)](#run-locally-cli)
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
| 🤖 **Automated Classification** | Categorizes tickets into `billing`, `account`, `technical`, or `general` |
| 🔥 **Priority Detection** | Assigns `high`, `medium`, or `low` based on customer tier and urgency keywords |
| 💬 **Dynamic Reasoning** | Generates human-readable explanations for every classification decision |
| 🌐 **REST API (FastAPI)** | Async HTTP API with Swagger UI, Pydantic validation and rate limiting |
| 📬 **Message Queues** | Celery + Redis for non-blocking asynchronous ticket processing |
| 🔔 **Webhook Notifications** | Sends rich Discord/Slack embeds when a ticket is assigned to a team |
| 🗄️ **Dual-Backend DB** | PostgreSQL in Docker/production; SQLite fallback for local/Streamlit Cloud |
| 🔒 **Secure Admin Panel** | Password-protected Streamlit dashboard for live rule management — no code changes needed |
| 📊 **Persistent History** | Processed tickets are stored in DB and survive page reloads |
| 🧠 **RegEx Matching** | Word-boundary (`\b`) patterns prevent false-positive substring hits |
| 🚦 **Rate Limiting** | `slowapi` protects the API endpoints (30 req/min for POST, 120/min for GET) |
| 📋 **Structured Logging** | Python `logging` module writes to `app.log` with timestamps |
| ✅ **26 Automated Tests** | Unit + E2E test suites covering edge cases, case tickets, and output format |
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
                        │   │ TicketEvaluator       │  │
                        │   │ TeamRouter            │  │
                        │   │ Notifier (Webhook)    │  │
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
- **Streamlit UI** (`app.py`) — Interactive dashboard with Admin Panel
- **CLI Batch Processor** (`main.py`) — Processes `data/tickets.json` directly

---

## Tech Stack

| Layer | Technology |
|---|---|
| **API Framework** | FastAPI + Uvicorn |
| **Async Processing** | Celery + Redis |
| **Database (Prod)** | PostgreSQL 16 |
| **Database (Dev)** | SQLite (auto-fallback) |
| **Web UI** | Streamlit |
| **Config** | `config/settings.py` + `.env` |
| **Rate Limiting** | slowapi |
| **Notifications** | Discord/Slack Webhooks via `requests` |
| **Testing** | pytest (26 tests: Unit + E2E) |
| **Containerization** | Docker + Docker Compose (5 services) |

---

## Project Structure

```
support-ticket-router/
│
├── api.py                    # FastAPI REST API entry point
├── worker.py                 # Celery async background worker
├── main.py                   # CLI batch processor (main assessment deliverable)
├── app.py                    # Streamlit UI + Admin Panel
│
├── config/
│   └── settings.py           # ✨ Central config — all env vars in one place
│
├── database/
│   └── db.py                 # Dual-backend DB (PostgreSQL + SQLite fallback)
│
├── engine/
│   ├── evaluator.py          # Classification engine (RegEx word-boundary matching)
│   ├── router.py             # Team routing engine
│   └── notifier.py           # Discord/Slack webhook dispatcher
│
├── models/
│   └── ticket.py             # Typed dataclasses (Ticket, ProcessedTicket)
│
├── tests/
│   ├── test_evaluator.py     # 11 unit tests
│   └── test_e2e.py           # 15 E2E pipeline tests (3 test classes)
│
├── data/
│   └── tickets.json          # Sample input (assessment data)
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

### Configuration (.env)

```bash
# Copy the template
cp .env.example .env
```

The `.env` file contains:

```env
# PostgreSQL
POSTGRES_USER=admin
POSTGRES_PASSWORD=secret123
POSTGRES_DB=ticket_db
DATABASE_URL=postgresql://admin:secret123@db:5432/ticket_db

# Redis
REDIS_URL=redis://redis:6379/0

# Admin Panel (change before production!)
ADMIN_PASSWORD=admin123

# Webhooks (optional)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

> **Security Note:** `.env` is git-ignored. Never commit real secrets to source control.

---

### Run with Docker (Recommended)

Starts **PostgreSQL**, **Redis**, **FastAPI**, **Celery Worker**, and **CLI** simultaneously:

```bash
docker compose up --build
```

Services will start in dependency order (DB and Redis first, then API and Worker). 

> [!NOTE]
> The `ticket-router-cli` service is a **run-once job**. It will process the sample tickets, print the results to the logs, and then exit. You can see its output with `docker compose logs ticket-router-cli`.

---

### Run Locally (CLI)

The core assessment deliverable — processes `data/tickets.json` and outputs results:

```bash
pip install -r requirements.txt
python main.py
```

Output is printed to console and saved to `data/processed_tickets.json`.

---

### Run Streamlit UI

```bash
streamlit run app.py
```

Or visit the live hosted version: 👉 **[https://support-ticket-router.streamlit.app/](https://support-ticket-router.streamlit.app/)**

**Admin Panel Access:**
1. Open left sidebar → click **Admin Panel**
2. Enter password: `admin123` (or your custom `ADMIN_PASSWORD`)
3. Add / edit / delete categories and keywords — changes take effect immediately, no restart needed

---

### Run Tests

```bash
pytest tests/ -v
```

**Expected output:** `26 passed`

| Test Suite | Count | Coverage |
|---|---|---|
| `test_evaluator.py` | 11 | Category classification, priority rules, edge cases |
| `test_e2e.py` | 15 | All 4 case tickets, empty list, None fields, malformed data, output format |

---

## REST API Reference

Base URL: `http://localhost:8000`

Interactive docs: **[http://localhost:8000/docs](http://localhost:8000/docs)** (Swagger UI)

### `POST /api/v1/process-ticket`

Enqueues a ticket for async classification. Returns a `task_id` immediately.

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

**Response `202`:**
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

**Response (while processing):**
```json
{
  "task_id": "8b52df3e-...",
  "status": "PENDING",
  "result": null
}
```

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
    "reason": "Classified as billing and marked high priority because customer is premium and billing ticket contains financial urgency keywords."
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
| `celery-worker` | Local build | — | Background ticket processor |
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

### Priority Rules

| Priority | Conditions |
|---|---|
| **High** | Customer type is `premium` **OR** message contains urgency keywords (`urgent`, `asap`, `blocked`, `cannot use`, ...) **OR** billing ticket with financial/legal urgency (`money`, `fraud`, `withdrawn`, `lawsuit`, `legal`, ...) |
| **Medium** | Category is `technical` or `account` |
| **Low** | All other cases |

> All rules are stored in the database and can be modified live via the Admin Panel — **no code changes required**.

---

## Assessment Q&A

### How did you break down the problem?

I adopted a highly modular, decoupled approach inspired by **Clean Architecture** principles:

1. **Data Models** (`models/ticket.py`) — Strictly typed `dataclass` schemas
2. **Config** (`config/settings.py`) — Single source of truth for all env variables
3. **Database Layer** (`database/db.py`) — Dual-backend (PostgreSQL/SQLite) with automatic fallback; rules injected at startup (Dependency Injection)
4. **Core Engines** (`engine/`) — Stateless, testable classes for classification, routing, and notifications
5. **Async Layer** (`worker.py`, `api.py`) — Celery + Redis decouple request intake from processing
6. **Interfaces** (`app.py`, `main.py`) — Streamlit UI with Admin Panel and CLI batch processor

### What assumptions did you make?

- Case insensitivity is required ("ReFunD" must match "refund")
- Tickets may have `None` or empty fields — all handled gracefully without crashing
- Multiple keyword matches across categories resolve by declaration order in DB
- JSON API uses `camelCase` externally; Python internals use `snake_case` (PEP 8) — mapping handled at the API boundary

### What edge cases did you handle?

- ✅ `None` / empty fields default to `general` / `low`
- ✅ Keywords inside punctuation are matched correctly
- ✅ False-positive substrings (`non-refundable` matching `refund`) — blocked via `\b` RegEx word boundaries
- ✅ Invalid ticket entries in a batch are skipped with a `WARNING` log, not crashing the entire run
- ✅ Empty ticket lists produce an empty output without errors
- ⚠️ Negation context (`"I do NOT want a refund"`) — intentionally ignored; requires NLP

### What would you change first if requirements evolved?

The system is already scaled through 5 development phases. The next step would be:

1. **NLP Classification** — Replace RegEx with HuggingFace transformers or OpenAI API for semantic intent detection
2. **Multi-Tenant Auth** — Replace the single admin password with OAuth2/JWT for multi-user management

---

## Roadmap

| Phase | Status | Description |
|---|---|---|
| Phase 1 | ✅ | Core engine: classification, priority, routing, JSON I/O |
| Phase 2 | ✅ | RegEx matching, E2E tests, structured logging |
| Phase 3 | ✅ | SQLite → PostgreSQL (dual-backend), Streamlit Admin Panel |
| Phase 4 | ✅ | FastAPI REST API, Celery + Redis async queues |
| Phase 5 | ✅ | Discord Webhooks, Docker Compose (5 services), multi-stage builds |
| Phase 6 | ✅ | Central config, rate limiting, ticket history persistence, 26 tests |
| Phase 7 | 🔜 | NLP/AI intent classification (HuggingFace / OpenAI) |
