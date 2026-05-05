import sqlite3
import os
import json

DB_PATH = "data/rules.db"

def get_connection(db_path=DB_PATH):
    """Returns an SQLite connection."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return sqlite3.connect(db_path)

def init_db(db_path=DB_PATH):
    """Initializes the database schema and seeds it if empty."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # Create Categories Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            keywords TEXT,
            assigned_team TEXT NOT NULL
        )
    ''')
    
    # Create Priority Rules Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS priority_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_type TEXT UNIQUE NOT NULL,
            keywords TEXT NOT NULL
        )
    ''')
    
    # Check if we need to seed data
    cursor.execute('SELECT COUNT(*) FROM categories')
    if cursor.fetchone()[0] == 0:
        # Seed Categories
        initial_categories = [
            ("billing", "refund,invoice,charge,payment,billing", "payments-team"),
            ("account", "password,login,authentication,account,access", "auth-team"),
            ("technical", "crash,bug,error,broken,loading", "technical-support"),
            ("general", "", "general-support") # General has no keywords
        ]
        cursor.executemany('''
            INSERT INTO categories (name, keywords, assigned_team) 
            VALUES (?, ?, ?)
        ''', initial_categories)
        
        # Seed Priority Rules
        initial_priority_rules = [
            ("urgency", "urgent,asap,emergency,immediately,blocked"),
            ("billing_urgency", "lawsuit,legal,fraud,scam")
        ]
        cursor.executemany('''
            INSERT INTO priority_rules (rule_type, keywords) 
            VALUES (?, ?)
        ''', initial_priority_rules)
        
        conn.commit()
    
    conn.close()

def get_category_rules(db_path=DB_PATH) -> dict:
    """Returns a dictionary of category -> list of keywords."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name, keywords FROM categories WHERE keywords != ''")
    rows = cursor.fetchall()
    conn.close()
    
    return {row[0]: [kw.strip() for kw in row[1].split(',')] for row in rows}

def get_team_mappings(db_path=DB_PATH) -> dict:
    """Returns a dictionary of category -> assigned team."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name, assigned_team FROM categories")
    rows = cursor.fetchall()
    conn.close()
    
    return {row[0]: row[1] for row in rows}

def get_priority_keywords(rule_type: str, db_path=DB_PATH) -> list:
    """Returns a list of keywords for a specific priority rule type."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT keywords FROM priority_rules WHERE rule_type = ?", (rule_type,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return [kw.strip() for kw in row[0].split(',')]
    return []

# --- Admin Panel CRUD Operations ---

def add_category(name: str, keywords: str, assigned_team: str, db_path=DB_PATH):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO categories (name, keywords, assigned_team) 
        VALUES (?, ?, ?)
    ''', (name.lower(), keywords.lower(), assigned_team))
    conn.commit()
    conn.close()

def update_category(old_name: str, new_name: str, keywords: str, assigned_team: str, db_path=DB_PATH):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE categories 
        SET name = ?, keywords = ?, assigned_team = ?
        WHERE name = ?
    ''', (new_name.lower(), keywords.lower(), assigned_team, old_name.lower()))
    conn.commit()
    conn.close()

def delete_category(name: str, db_path=DB_PATH):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM categories WHERE name = ?', (name.lower(),))
    conn.commit()
    conn.close()

def update_priority_keywords(rule_type: str, keywords: str, db_path=DB_PATH):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE priority_rules 
        SET keywords = ?
        WHERE rule_type = ?
    ''', (keywords.lower(), rule_type))
    conn.commit()
    conn.close()

def get_all_categories_raw(db_path=DB_PATH) -> list:
    """Returns raw rows for the admin panel: (id, name, keywords, assigned_team)"""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, keywords, assigned_team FROM categories")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "keywords": r[2], "assigned_team": r[3]} for r in rows]

def get_all_priority_rules_raw(db_path=DB_PATH) -> list:
    """Returns raw rows for the admin panel: (id, rule_type, keywords)"""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, rule_type, keywords FROM priority_rules")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "rule_type": r[1], "keywords": r[2]} for r in rows]

