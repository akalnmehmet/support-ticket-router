# Support Ticket Router

An intelligent, rule-based engine that processes customer support tickets and classifies them based on predefined business rules. Built as part of the Software Development Internship assessment at Uruba Software.

**🌐 Live Demo:** [https://support-ticket-router.streamlit.app/](https://support-ticket-router.streamlit.app/)

## Features

- **Automated Classification**: Automatically routes tickets into `billing`, `account`, `technical`, or `general` categories.
- **Priority Detection**: Determines ticket priority (`high`, `medium`, `low`) by analyzing customer tiers and semantic urgency keywords.
- **Dynamic Reasoning**: Generates intelligent, human-readable explanations detailing *why* a specific classification was made.
- **Live Interactive UI**: A fully hosted responsive web interface powered by Streamlit for instant visual testing.
- **Dockerized CLI**: Containerized batch processing to test JSON input/output effortlessly.
- **Test-Driven**: Comprehensive unit tests covering various edge cases and complex scenarios.

---

## Assessment Questions (Approach & Methodology)

### How did you break down the problem?
I adopted a highly modular, decoupled approach inspired by Clean Architecture principles:
1. **Data Models (`models/ticket.py`)**: Defined strictly typed schemas using Python's `dataclasses` to represent incoming data and output formats.
2. **Rules Configuration (`config/rules.py`)**: Abstracted all classification keywords and team routing rules into a central configuration file. This data-driven approach means adding a new category doesn't require modifying the core logic.
3. **Core Engine (`engine/evaluator.py` & `engine/router.py`)**: Built isolated classes that process the models strictly based on the configured rules.
4. **Presentation/Execution (`main.py` & `app.py`)**: Provided a CLI runner for automated JSON batch processing, alongside an interactive web interface.

### What assumptions did you make?
- Case insensitivity is required (e.g., "ReFunD" should match "refund").
- Real-world ticket JSONs might have missing fields (like an empty subject).
- If multiple keywords are matched across different categories, the system should prioritize them in the order they are defined in the config file.
- The standard JSON casing convention is `camelCase` for web APIs but `snake_case` internally in Python (PEP 8). I mapped inputs (`customerType` → `customer_type`) and outputs (`assigned_team` → `assignedTeam`) to respect both.

### What edge cases did you handle or intentionally ignore?
- **Handled**: Empty strings or `None` values for subjects and messages default gracefully to `general`/`low` without crashing.
- **Handled**: Keywords embedded inside punctuation.
- **Handled**: Case sensitivity is entirely normalized.
- **Ignored**: I intentionally ignored deep NLP contextual matching. For example, "I am *not* asking for a refund" will still trigger the refund keyword. A full NLP model was deemed out-of-scope for a rule-based assessment.

### What part of your solution would you change first if requirements evolved?
If requirements evolved to handle thousands of rules or multiple languages, I would:
1. Move `config/rules.py` into a database (like PostgreSQL or Redis) to allow dynamic rule updates without restarting the application.
2. Replace simple substring matching (`keyword in text`) with Regular Expressions (RegEx) or an NLP library (like `spaCy`) to ensure we only match whole words and understand context/negation better.

---

## How to Test and Run the Project

First, clone the repository to your local machine:
```bash
git clone https://github.com/akalnmehmet/support-ticket-router.git
cd support-ticket-router
```

You can then run and test this project in different ways depending on your preference.

### 1. Web UI Mode (Live Hosted App)
You don't need to install anything to test the logic visually. I have deployed the interactive Streamlit application online:
👉 **[Click here to test the live Support Ticket Router UI](https://support-ticket-router.streamlit.app/)**

### 2. CLI Mode via Docker (Batch Processing)
To process the raw input data exactly as requested in the assignment (`data/tickets.json` -> console/JSON output) without installing Python locally:

1. Ensure Docker Desktop is running.
2. Run the following command in your terminal:
   ```bash
   docker compose up --build
   ```
*Docker will parse the JSON, process the logic, print the formatted output to the console, and securely map the results to `data/processed_tickets.json` on your local machine.*

### 3. CLI Mode via Local Python
If you prefer to run the CLI processor directly with your local Python installation:
```bash
python main.py
```

### 4. Running the Unit Tests
To mathematically verify all edge cases, priority rules, and categorical mappings:
```bash
python -m unittest tests/test_evaluator.py
```
