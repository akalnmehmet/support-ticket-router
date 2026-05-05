# Support Ticket Router

An intelligent, rule-based engine that processes customer support tickets and classifies them based on predefined business rules. Built as part of the Software Development Internship assessment at Uruba Software.

## Features

- **Automated Classification**: Automatically routes tickets into `billing`, `account`, `technical`, or `general` categories.
- **Priority Detection**: Determines ticket priority (`high`, `medium`, `low`) by analyzing customer tiers and semantic urgency keywords.
- **Dynamic Reasoning**: Generates intelligent, human-readable explanations detailing *why* a specific classification was made.
- **Interactive UI**: Includes a responsive web interface powered by Streamlit for instant visual testing.
- **Dockerized**: Fully containerized for a 100% plug-and-play experience.
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

## How to Test and Run the ProjectYou can run this project in different ways depending on your preference.

### 1. Web UI Mode (Interactive Streamlit App)
We built a modern, interactive web interface so you can test various keywords, customer types, and edge cases instantly without changing the code.

**Using Docker (Recommended):**
1. Ensure Docker Desktop is running.
2. Run `docker compose up --build` in your terminal.
3. Open your browser and navigate to **`http://localhost:8501`**

**Using Python Locally (Without Docker):**
1. Install dependencies: `pip install streamlit`
2. Run the app: `streamlit run app.py`

### 2. CLI Mode (Batch Processing via `main.py`)
If you prefer to process the raw input data exactly as requested in the assignment (reading from `data/tickets.json` and outputting a JSON array):

1. Ensure you have Python installed.
2. Run the main script in the terminal:
   ```bash
   python main.py
   ```
*This will parse the JSON, process the logic, print the formatted output to the console, and save the results into `data/processed_tickets.json`.*

### 3. Running the Unit Tests
To mathematically verify all edge cases, priority rules, and categorical mappings:
```bash
python -m unittest tests/test_evaluator.py
```
