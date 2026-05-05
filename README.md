# Support Ticket Router

An intelligent, rule-based engine that processes customer support tickets and classifies them based on predefined business rules. Built as part of the Software Development Internship assessment at Uruba Software.

**🌐 Live Demo:** [https://support-ticket-router.streamlit.app/](https://support-ticket-router.streamlit.app/)

---

## Features

| Feature | Details |
|---|---|
| 🤖 **Automated Classification** | Routes tickets into `billing`, `account`, `technical`, or `general` categories |
| 🔥 **Priority Detection** | Analyzes customer tier and urgency keywords to assign `high`, `medium`, or `low` priority |
| 🌐 **REST API Microservice** | Fully async FastAPI backend with Pydantic validation and Swagger UI |
| 📬 **Message Queues** | Celery + Redis for asynchronous ticket processing — zero API blocking |
| 🔔 **Webhook Notifications** | Notifies Slack/Discord teams with rich embeds when a ticket is assigned |
| 🗄️ **PostgreSQL Database** | Production-grade relational DB (migrated from SQLite) with persistent Docker volumes |
| 🔒 **Secure Admin Panel** | Password-protected Streamlit dashboard to manage classification rules without code changes |
| 🧠 **Regex Matching** | Word boundary (`\b`) matching prevents false-positive substring hits |
| 📋 **Production Logging** | `logging` module writes structured entries to `app.log` |
| ✅ **Test-Driven** | Unit + E2E pytest suites covering the full processing pipeline |

---

## Architecture Overview

```
[Client / Web Form]
       │
       ▼
[FastAPI REST API :8000]   ──── POST /api/v1/process-ticket
       │  enqueues task
       ▼
[Redis Message Broker]
       │  dequeues task
       ▼
[Celery Worker]
    ├── Reads rules from PostgreSQL
    ├── Classifies ticket (Evaluator → Router)
    ├── Stores result in Redis Backend
    └── Sends Webhook to Slack/Discord
       │
       ▼
[GET /api/v1/task/{task_id}]  ──── Poll for result
```

---

## Assessment Questions (Approach & Methodology)

### How did you break down the problem?
I adopted a highly modular, decoupled approach inspired by **Clean Architecture** principles:
1. **Data Models (`models/ticket.py`)**: Strictly typed `dataclass` schemas for input/output.
2. **Database Layer (`database/db.py`)**: PostgreSQL-backed persistent store for all classification rules. Rules are cached at startup via Dependency Injection — zero per-request DB overhead.
3. **Core Engine (`engine/evaluator.py`, `engine/router.py`)**: Stateless classes that classify tickets using injected rules.
4. **Notification Engine (`engine/notifier.py`)**: Sends rich-embed Discord/Slack webhooks on ticket routing.
5. **Async Layer (`worker.py`, `api.py`)**: Celery + Redis decouple request intake from processing.
6. **Interfaces (`app.py`, `main.py`)**: Streamlit UI with Admin Panel and a CLI batch processor.

### What assumptions did you make?
- Case insensitivity is required ("ReFunD" must match "refund").
- Real-world tickets may have `None` or empty fields — all handled gracefully.
- Multiple keyword matches across categories should resolve by declaration order.
- JSON API uses `camelCase` externally; Python internals use `snake_case` (PEP 8). Mapping is handled at API boundary.

### What edge cases did you handle or intentionally ignored?
- ✅ `None` / empty fields default gracefully to `general` / `low`
- ✅ Punctuation-embedded keywords are matched correctly
- ✅ False-positive substrings (`non-refundable` matching `refund`) blocked via `\b` RegEx
- ⚠️ Negation context (`"I do NOT want a refund"`) — intentionally ignored; requires NLP

### What would you change first if requirements evolved?
The system is already on a 4-phase roadmap. The next logical step is replacing RegEx with ML/NLP-based intent classification (e.g., HuggingFace transformers or OpenAI API).

---

## How to Run

### Prerequisites
- Docker Desktop installed and running
- Git

### 1. Clone the repository
```bash
git clone https://github.com/akalnmehmet/support-ticket-router.git
cd support-ticket-router
```

### 2. Configure Environment
```bash
cp .env.example .env
# Optionally edit .env to set a custom DB password or Discord webhook URL
```

### 3. Start All Services (Recommended)
One command brings up PostgreSQL, Redis, API, and Celery Worker simultaneously:
```bash
docker compose up --build
```

### 4. Test the REST API (Swagger UI)
Open your browser and go to:
**[http://localhost:8000/docs](http://localhost:8000/docs)**

Try the `POST /api/v1/process-ticket` endpoint with this JSON body:
```json
{
  "id": 1001,
  "subject": "Urgent refund request",
  "message": "My payment was charged twice, this is fraud!",
  "customerType": "premium",
  "createdAt": "2026-05-05T10:00:00Z"
}
```
Copy the returned `task_id` and poll `GET /api/v1/task/{task_id}` to see the classification result.

### 5. Test the Streamlit UI & Admin Panel
Visit the live hosted app:
👉 **[https://support-ticket-router.streamlit.app/](https://support-ticket-router.streamlit.app/)**

To access the Admin Panel:
1. Click **Admin Panel** in the left sidebar
2. Enter password: `admin123`
3. Add/edit/delete categories and priority keywords live — no restart needed!

### 6. CLI Mode (Batch Processing)
To process `data/tickets.json` locally:
```bash
pip install -r requirements.txt
python main.py
```

### 7. Run Unit & E2E Tests
```bash
pytest tests/ -v
```

---

## Project Structure

```
support-ticket-router/
├── api.py                  # FastAPI REST API entry point
├── worker.py               # Celery async worker
├── main.py                 # CLI batch processor
├── app.py                  # Streamlit web UI + Admin Panel
├── database/
│   └── db.py               # PostgreSQL CRUD layer
├── engine/
│   ├── evaluator.py        # Classification engine (RegEx-based)
│   ├── router.py           # Team routing engine
│   └── notifier.py         # Discord/Slack webhook dispatcher
├── models/
│   └── ticket.py           # Typed dataclasses
├── tests/
│   ├── test_evaluator.py   # Unit tests (12 cases)
│   └── test_e2e.py         # End-to-End pipeline tests
├── data/
│   └── tickets.json        # Sample input data
├── docker-compose.yml      # 5-service orchestration
├── Dockerfile
├── requirements.txt
├── .env.example            # Configuration template
└── README.md
```

---

## Docker Services

| Service | Container | Port | Role |
|---|---|---|---|
| `db` | `ticket-router-db` | 5432 | PostgreSQL 16 database |
| `redis` | `ticket-router-redis` | 6379 | Celery broker & result backend |
| `ticket-router-api` | `ticket-router-api` | 8000 | FastAPI REST API |
| `celery-worker` | `ticket-router-worker` | — | Background ticket processor |
| `ticket-router-cli` | `ticket-router-cli` | — | Batch JSON processor |
