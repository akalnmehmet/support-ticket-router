"""
Dual-backend database module.
- If DATABASE_URL environment variable is set (Docker/Production) → PostgreSQL via psycopg2
- If not set (Streamlit Cloud / local dev) → SQLite via sqlite3 (zero dependencies)
"""

import os
import logging
from config.settings import DATABASE_URL, SQLITE_PATH

logger = logging.getLogger(__name__)

# ─── Backend Detection ──────────────────────────────────────────────────────

def _is_postgres() -> bool:
    return DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://")


# ─── Connection Factory ─────────────────────────────────────────────────────

def get_connection():
    if _is_postgres():
        import psycopg2
        return psycopg2.connect(DATABASE_URL)
    else:
        import sqlite3, os
        os.makedirs(os.path.dirname(SQLITE_PATH), exist_ok=True)
        return sqlite3.connect(SQLITE_PATH)


# ─── Placeholder syntax per backend ─────────────────────────────────────────

def _ph() -> str:
    """Returns the query placeholder: %s for Postgres, ? for SQLite."""
    return "%s" if _is_postgres() else "?"


def _serial() -> str:
    return "SERIAL" if _is_postgres() else "INTEGER"


# ─── Schema & Seeding ────────────────────────────────────────────────────────

def init_db():
    """Initializes the database schema and seeds it with default rules if empty."""
    conn = get_connection()
    cursor = conn.cursor()
    serial = _serial()

    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS categories (
            id {serial} PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            keywords TEXT,
            assigned_team VARCHAR(100) NOT NULL
        )
    ''')

    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS priority_rules (
            id {serial} PRIMARY KEY,
            rule_type VARCHAR(100) UNIQUE NOT NULL,
            keywords TEXT NOT NULL
        )
    ''')

    # Seed if empty
    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        ph = _ph()
        initial_categories = [
            ("billing", "refund,invoice,charge,payment,billing,money,paid,card,withdrawn", "payments-team"),
            ("account", "password,login,authentication,account,access", "account-support"),
            ("technical", "crash,bug,error,broken,loading,upload,not working", "technical-support"),
            ("general", "", "general-support"),
        ]
        cursor.executemany(
            f"INSERT INTO categories (name, keywords, assigned_team) VALUES ({ph}, {ph}, {ph})",
            initial_categories
        )

        initial_priority_rules = [
            ("urgency", "urgent,asap,emergency,immediately,blocked,cannot use"),
            ("billing_urgency", "lawsuit,legal,fraud,scam,money,withdrawn,refund"),
        ]
        cursor.executemany(
            f"INSERT INTO priority_rules (rule_type, keywords) VALUES ({ph}, {ph})",
            initial_priority_rules
        )
        logger.info("Database seeded with default rules.")

    # Create Processed Tickets history table
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS processed_tickets (
            id {serial} PRIMARY KEY,
            ticket_id INTEGER,
            subject TEXT,
            message TEXT,
            customer_type TEXT,
            category TEXT,
            priority TEXT,
            assigned_team TEXT,
            reason TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    cursor.close()
    conn.close()
    logger.info(f"Database initialized ({'PostgreSQL' if _is_postgres() else 'SQLite'}).")


# ─── Read Operations ─────────────────────────────────────────────────────────

def get_category_rules() -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, keywords FROM categories WHERE keywords != ''")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return {row[0]: [kw.strip() for kw in row[1].split(",")] for row in rows}


def get_team_mappings() -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, assigned_team FROM categories")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return {row[0]: row[1] for row in rows}


def get_priority_keywords(rule_type: str) -> list:
    ph = _ph()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT keywords FROM priority_rules WHERE rule_type = {ph}", (rule_type,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        return [kw.strip() for kw in row[0].split(",")]
    return []


# ─── Admin Panel CRUD Operations ─────────────────────────────────────────────

def add_category(name: str, keywords: str, assigned_team: str):
    ph = _ph()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"INSERT INTO categories (name, keywords, assigned_team) VALUES ({ph}, {ph}, {ph})",
        (name.lower(), keywords.lower(), assigned_team)
    )
    conn.commit()
    cursor.close()
    conn.close()


def update_category(old_name: str, new_name: str, keywords: str, assigned_team: str):
    ph = _ph()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE categories SET name = {ph}, keywords = {ph}, assigned_team = {ph} WHERE name = {ph}",
        (new_name.lower(), keywords.lower(), assigned_team, old_name.lower())
    )
    conn.commit()
    cursor.close()
    conn.close()


def delete_category(name: str):
    ph = _ph()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM categories WHERE name = {ph}", (name.lower(),))
    conn.commit()
    cursor.close()
    conn.close()


def update_priority_keywords(rule_type: str, keywords: str):
    ph = _ph()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE priority_rules SET keywords = {ph} WHERE rule_type = {ph}",
        (keywords.lower(), rule_type)
    )
    conn.commit()
    cursor.close()
    conn.close()


def get_all_categories_raw() -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, keywords, assigned_team FROM categories")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [{"id": r[0], "name": r[1], "keywords": r[2], "assigned_team": r[3]} for r in rows]


def get_all_priority_rules_raw() -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, rule_type, keywords FROM priority_rules")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [{"id": r[0], "rule_type": r[1], "keywords": r[2]} for r in rows]


# ─── Processed Ticket History ─────────────────────────────────────────────────

def save_processed_ticket(ticket_data: dict, result: dict):
    """Persists a classified ticket to the processed_tickets history table."""
    ph = _ph()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"""INSERT INTO processed_tickets
            (ticket_id, subject, message, customer_type, category, priority, assigned_team, reason)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})""",
        (
            ticket_data.get("id"),
            ticket_data.get("subject", ""),
            ticket_data.get("message", ""),
            ticket_data.get("customerType", "standard"),
            result.get("category"),
            result.get("priority"),
            result.get("assignedTeam"),
            result.get("reason"),
        )
    )
    conn.commit()
    cursor.close()
    conn.close()


def get_recent_processed_tickets(limit: int = 50) -> list:
    """Returns the most recently processed tickets for the UI history view."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT ticket_id, subject, customer_type, category, priority, assigned_team, reason, processed_at "
        "FROM processed_tickets ORDER BY processed_at DESC LIMIT ?".replace("?", _ph()),
        (limit,)
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [
        {
            "id": r[0], "subject": r[1], "customer_type": r[2],
            "category": r[3], "priority": r[4], "team": r[5],
            "reason": r[6], "timestamp": str(r[7])
        }
        for r in rows
    ]
