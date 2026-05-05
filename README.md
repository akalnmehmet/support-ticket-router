# Support Ticket Router

An intelligent, rule-based engine that processes customer support tickets and classifies them based on predefined business rules. Built as part of the Software Development Internship assessment at Uruba Software.

**🌐 Live Demo:** [https://support-ticket-router.streamlit.app/](https://support-ticket-router.streamlit.app/)

## Features

- **Automated Classification**: Automatically routes tickets into `billing`, `account`, `technical`, or `general` categories.
- **Priority Detection**: Determines ticket priority (`high`, `medium`, `low`) by analyzing customer tiers and semantic urgency keywords.
- **REST API Microservice**: Fully functional backend API powered by **FastAPI** and **Pydantic** for seamless JSON communication.
- **Database Integrated**: Uses **SQLite** for persisting classification rules, completely decoupling logic from configuration.
- **Secure Admin Panel**: A password-protected dashboard to dynamically add, edit, and delete categorization rules without touching the code.
- **Advanced Text Matching**: Uses Regular Expressions (RegEx) with word boundaries (`\b`) to eliminate false-positive substring matches.
- **Production-Ready Logging**: Tracks system health and execution via Python's standard `logging` module outputting to `app.log`.
- **Test-Driven**: Comprehensive Unit and End-to-End (E2E) test suites using `pytest` to guarantee flawless execution pipelines.

---

## Assessment Questions (Approach & Methodology)

### How did you break down the problem?
I adopted a highly modular, decoupled approach inspired by Clean Architecture principles:
1. **Data Models (`models/ticket.py`)**: Defined strictly typed schemas using Python's `dataclasses` to represent incoming data and internal formats.
2. **Database & State (`database/db.py`)**: Abstracted all classification keywords and team routing rules into an SQLite database. Rules are cached at startup and injected into the engines (Dependency Injection) to ensure extreme performance (0 bottleneck).
3. **Core Engine (`engine/evaluator.py` & `engine/router.py`)**: Built isolated, stateless classes that process the models based on the injected rules.
4. **Presentation/Execution (`api.py`, `main.py`, `app.py`)**: Exposed the engine through three distinct interfaces: A REST API, a CLI batch processor, and an interactive Streamlit web UI.

### What assumptions did you make?
- Case insensitivity is required (e.g., "ReFunD" should match "refund").
- Real-world ticket JSONs might have missing fields (like an empty subject).
- If multiple keywords are matched across different categories, the system should prioritize them in the order they are defined in the database.
- The standard JSON casing convention is `camelCase` for web APIs but `snake_case` internally in Python (PEP 8). I mapped inputs and outputs back and forth to respect both boundaries.

### What edge cases did you handle or intentionally ignore?
- **Handled**: Empty strings or `None` values for subjects and messages default gracefully to `general`/`low` without crashing.
- **Handled**: Keywords embedded inside punctuation.
- **Handled**: Case sensitivity is entirely normalized.
- **Handled**: False-positive substrings (e.g. "non-refundable" triggering "refund") are prevented using RegEx word boundaries (`\b`).
- **Ignored**: I intentionally ignored deep NLP contextual matching. For example, "I am *not* asking for a refund" will still trigger the refund keyword. A full NLP model was deemed out-of-scope for a rule-based assessment.

### What part of your solution would you change first if requirements evolved?
We have already scaled this from a simple script to a DB-driven API. If requirements evolved further to handle massive enterprise scale, I would:
1. **Message Queues**: Integrate RabbitMQ or Celery so that high-volume incoming API requests are placed in an asynchronous queue rather than processed sequentially.
2. **True Intent Classification**: Replace RegEx matching with Machine Learning/NLP models (like HuggingFace or spaCy) for semantic sentiment and intent analysis.

---

## How to Test and Run the Project

First, clone the repository to your local machine:
```bash
git clone https://github.com/akalnmehmet/support-ticket-router.git
cd support-ticket-router
```

You can test this project in 4 different ways depending on your preference.

### 1. Web UI & Admin Panel (Live Hosted App)
You don't need to install anything to test the logic visually.
👉 **[Click here to test the live Support Ticket Router UI](https://support-ticket-router.streamlit.app/)**

*Want to test the dynamic database?* Open the left sidebar, go to **Admin Panel**, login with the password `admin123`, and try adding a new category!

### 2. REST API via Docker (FastAPI)
To test the API endpoints exactly how another microservice would communicate with it:

1. Ensure Docker Desktop is running.
2. Run the following command in your terminal:
   ```bash
   docker compose up --build
   ```
3. Open your browser and go to: **[http://localhost:8000/docs](http://localhost:8000/docs)**
*This will open the automated Swagger UI where you can send mock JSON requests to the `POST /api/v1/process-ticket` endpoint.*

### 3. CLI Mode via Local Python (Batch Processing)
To process the raw input data exactly as requested in the assignment (`data/tickets.json` -> console/JSON output):
```bash
pip install -r requirements.txt
python main.py
```

### 4. Running the Unit & E2E Tests
To mathematically verify all edge cases, priority rules, and the full data pipeline:
```bash
pytest tests/ -v
```
