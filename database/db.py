import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:secret123@localhost:5432/ticket_db")


def get_connection():
    """Returns a PostgreSQL connection using DATABASE_URL from environment."""
    return psycopg2.connect(DATABASE_URL)


def init_db():
    """Initializes the database schema and seeds it with default rules if empty."""
    conn = get_connection()
    cursor = conn.cursor()

    # Create Categories Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            keywords TEXT,
            assigned_team VARCHAR(100) NOT NULL
        )
    ''')

    # Create Priority Rules Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS priority_rules (
            id SERIAL PRIMARY KEY,
            rule_type VARCHAR(100) UNIQUE NOT NULL,
            keywords TEXT NOT NULL
        )
    ''')

    # Seed if empty
    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        initial_categories = [
            ("billing", "refund,invoice,charge,payment,billing", "payments-team"),
            ("account", "password,login,authentication,account,access", "auth-team"),
            ("technical", "crash,bug,error,broken,loading", "technical-support"),
            ("general", "", "general-support"),
        ]
        cursor.executemany(
            "INSERT INTO categories (name, keywords, assigned_team) VALUES (%s, %s, %s)",
            initial_categories
        )

        initial_priority_rules = [
            ("urgency", "urgent,asap,emergency,immediately,blocked"),
            ("billing_urgency", "lawsuit,legal,fraud,scam"),
        ]
        cursor.executemany(
            "INSERT INTO priority_rules (rule_type, keywords) VALUES (%s, %s)",
            initial_priority_rules
        )
        logger.info("Database seeded with default rules.")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Database initialized successfully.")


def get_category_rules() -> dict:
    """Returns a dictionary of category -> list of keywords."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, keywords FROM categories WHERE keywords != ''")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return {row[0]: [kw.strip() for kw in row[1].split(",")] for row in rows}


def get_team_mappings() -> dict:
    """Returns a dictionary of category -> assigned team."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, assigned_team FROM categories")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return {row[0]: row[1] for row in rows}


def get_priority_keywords(rule_type: str) -> list:
    """Returns a list of keywords for a specific priority rule type."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT keywords FROM priority_rules WHERE rule_type = %s", (rule_type,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        return [kw.strip() for kw in row[0].split(",")]
    return []


# --- Admin Panel CRUD Operations ---

def add_category(name: str, keywords: str, assigned_team: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO categories (name, keywords, assigned_team) VALUES (%s, %s, %s)",
        (name.lower(), keywords.lower(), assigned_team)
    )
    conn.commit()
    cursor.close()
    conn.close()


def update_category(old_name: str, new_name: str, keywords: str, assigned_team: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE categories SET name = %s, keywords = %s, assigned_team = %s WHERE name = %s",
        (new_name.lower(), keywords.lower(), assigned_team, old_name.lower())
    )
    conn.commit()
    cursor.close()
    conn.close()


def delete_category(name: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM categories WHERE name = %s", (name.lower(),))
    conn.commit()
    cursor.close()
    conn.close()


def update_priority_keywords(rule_type: str, keywords: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE priority_rules SET keywords = %s WHERE rule_type = %s",
        (keywords.lower(), rule_type)
    )
    conn.commit()
    cursor.close()
    conn.close()


def get_all_categories_raw() -> list:
    """Returns raw rows for the admin panel."""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT id, name, keywords, assigned_team FROM categories")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(r) for r in rows]


def get_all_priority_rules_raw() -> list:
    """Returns raw rows for the admin panel."""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT id, rule_type, keywords FROM priority_rules")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(r) for r in rows]
