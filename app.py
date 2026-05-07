import streamlit as st
import os
import datetime
import random
import pandas as pd

from models.ticket import Ticket
from engine.evaluator import TicketEvaluator
from engine.router import TeamRouter
from engine.ai_classifier import HybridClassifier
from database.db import (
    init_db, get_category_rules, get_team_mappings, get_priority_keywords,
    get_all_categories_raw, get_all_priority_rules_raw,
    add_category, update_category, delete_category, update_priority_keywords,
    get_recent_processed_tickets
)
from config import settings
from config.settings import ADMIN_PASSWORD

# ── Helpers ───────────────────────────────────────────────────────────────────

@st.cache_resource
def setup_database():
    init_db()
    return {
        "category_rules": get_category_rules(),
        "team_mapping": get_team_mappings(),
        "urgency_keywords": get_priority_keywords("urgency"),
        "billing_urgency_keywords": get_priority_keywords("billing_urgency"),
    }


@st.cache_resource
def setup_classifier(_rules: dict) -> HybridClassifier:
    """Build the HybridClassifier once and cache it for the session."""
    evaluator = TicketEvaluator(
        _rules["category_rules"],
        _rules["urgency_keywords"],
        _rules["billing_urgency_keywords"],
    )
    router = TeamRouter(_rules["team_mapping"])

    ai_provider = None
    provider_name = (settings.AI_PROVIDER or "none").lower()
    if provider_name == "gemini" and settings.GEMINI_API_KEY:
        try:
            from engine.providers.gemini_provider import GeminiProvider
            ai_provider = GeminiProvider(settings.GEMINI_API_KEY, settings.GEMINI_MODEL)
        except Exception:
            pass

    return HybridClassifier(
        evaluator=evaluator,
        router=router,
        ai_provider=ai_provider,
        confidence_threshold=settings.AI_CONFIDENCE_THRESHOLD,
    )


def load_css():
    css_path = os.path.join(os.path.dirname(__file__), "assets", "styles.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    # Extra inline styles for AI badge and confidence bar
    st.markdown("""
    <style>
    .badge-ai {
        display: inline-flex; align-items: center; gap: 6px;
        background: linear-gradient(135deg, #6c63ff, #3ecfcf);
        color: #fff; font-size: 0.78rem; font-weight: 700;
        padding: 4px 12px; border-radius: 20px;
        box-shadow: 0 0 10px rgba(108,99,255,0.5);
        letter-spacing: 0.03em;
    }
    .badge-regex {
        display: inline-flex; align-items: center; gap: 6px;
        background: linear-gradient(135deg, #444, #666);
        color: #ccc; font-size: 0.78rem; font-weight: 700;
        padding: 4px 12px; border-radius: 20px;
        letter-spacing: 0.03em;
    }
    .confidence-wrap { margin: 6px 0 10px 0; }
    .confidence-label { font-size: 0.75rem; color: #aaa; margin-bottom: 4px; }
    .confidence-bar-bg {
        background: #2a2a3a; border-radius: 8px; height: 8px; overflow: hidden;
    }
    .confidence-bar-fill {
        height: 8px; border-radius: 8px;
        background: linear-gradient(90deg, #6c63ff, #3ecfcf);
        transition: width 0.4s ease;
    }
    </style>
    """, unsafe_allow_html=True)


def _ai_badge_html(ai_used: bool, confidence: float, model: str) -> str:
    """Returns the HTML for the AI/RegEx badge + confidence bar."""
    if ai_used:
        badge = f'<span class="badge-ai">✨ AI · {model}</span>'
        pct = int(confidence * 100)
        bar = f"""
        <div class="confidence-wrap">
          <div class="confidence-label">Confidence: {pct}%</div>
          <div class="confidence-bar-bg">
            <div class="confidence-bar-fill" style="width:{pct}%"></div>
          </div>
        </div>"""
    else:
        badge = '<span class="badge-regex">⚙️ RegEx Engine</span>'
        bar = ""
    return badge + bar


# ── Dashboard ─────────────────────────────────────────────────────────────────

def render_dashboard(rules):
    st.title("Support Ticket Classification Engine")
    st.write(
        "An intelligent engine that categorizes, prioritizes, and routes customer "
        "support tickets automatically — powered by AI with a rule-based fallback."
    )

    # Show active provider in sidebar info box
    provider_name = (settings.AI_PROVIDER or "none").lower()
    if provider_name == "gemini" and settings.GEMINI_API_KEY:
        st.sidebar.success(f"🤖 AI: Gemini · `{settings.GEMINI_MODEL}`")
    else:
        st.sidebar.info("⚙️ Mode: RegEx Engine")

    # Load ticket history from DB (persists across page reloads)
    if "ticket_history" not in st.session_state:
        try:
            st.session_state.ticket_history = get_recent_processed_tickets(50)
        except Exception:
            st.session_state.ticket_history = []

    # Input form
    with st.form("ticket_form", clear_on_submit=True):
        subject = st.text_input("Subject", placeholder="Brief summary of the issue...")
        message = st.text_area(
            "Message", placeholder="Detailed explanation of the problem...", height=150
        )
        customer_type = st.selectbox("Customer Type", options=["Standard", "Premium"])
        submitted = st.form_submit_button("🚀 Process Ticket")

    # Processing
    if submitted:
        if not subject.strip() and not message.strip():
            st.warning("Please provide at least a subject or a message to process.")
        else:
            classifier = setup_classifier(rules)
            ticket_id = random.randint(10000, 99999)
            current_time = datetime.datetime.utcnow().isoformat() + "Z"

            ticket = Ticket(
                id=ticket_id,
                subject=subject,
                message=message,
                customer_type=customer_type,
                created_at=current_time,
            )

            with st.spinner("Analyzing ticket..."):
                pt = classifier.process(ticket)

            result = {
                "id": ticket_id,
                "subject": subject,
                "customer_type": customer_type,
                "category": pt.category,
                "priority": pt.priority,
                "team": pt.assigned_team,
                "reason": pt.reason,
                "timestamp": current_time,
                "ai_used": pt.ai_used,
                "confidence": pt.confidence,
            }

            # Persist to DB
            try:
                from database.db import save_processed_ticket
                save_processed_ticket(
                    {"id": ticket_id, "subject": subject, "message": message,
                     "customerType": customer_type},
                    {"category": pt.category, "priority": pt.priority,
                     "assignedTeam": pt.assigned_team, "reason": pt.reason},
                )
            except Exception:
                pass

            st.session_state.ticket_history.insert(0, result)

    # Results history
    if st.session_state.ticket_history:
        st.markdown("---")
        st.subheader("Classification Results History")

        for idx, item in enumerate(st.session_state.ticket_history):
            ai_used = item.get("ai_used", False)
            confidence = item.get("confidence", 1.0)
            model_label = settings.GEMINI_MODEL if ai_used else "regex"

            expander_label = (
                f"🎫 Ticket #{item['id']} | "
                f"Priority: {item['priority'].upper()} | "
                f"{item['category'].title()} | "
                f"{'✨ AI' if ai_used else '⚙️ RegEx'}"
            )

            with st.expander(expander_label, expanded=(idx == 0)):
                # AI / RegEx badge + confidence bar
                st.markdown(
                    _ai_badge_html(ai_used, confidence, model_label),
                    unsafe_allow_html=True,
                )

                col1, col2, col3 = st.columns(3)
                col1.metric("📌 Category", item["category"].title())
                col2.metric("🔥 Priority", item["priority"].title())
                col3.metric("🏢 Assigned Team", item["team"].title().replace("-", " "))

                st.write(f"**Subject:** {item['subject']}")
                st.write(f"**Customer Type:** {item['customer_type']}")
                st.info(f"**Reasoning:** {item['reason']}")


# ── Admin Login ───────────────────────────────────────────────────────────────

def render_admin_login():
    st.title("🔒 Admin Login")
    st.write("Please enter the administrator password to manage system rules.")

    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if password == ADMIN_PASSWORD:
            st.session_state.is_admin = True
            st.rerun()
        else:
            st.error("Invalid password!")


# ── Admin Panel ───────────────────────────────────────────────────────────────

def render_admin_panel():
    st.title("⚙️ Admin Panel")
    st.write(
        "Manage ticket classification categories and priority keywords directly from the database."
    )

    if st.button("Logout"):
        st.session_state.is_admin = False
        st.rerun()

    st.markdown("---")
    st.subheader("1. Priority Keywords")
    priority_rules = get_all_priority_rules_raw()

    for rule in priority_rules:
        with st.form(f"form_priority_{rule['id']}"):
            st.write(f"**Rule Type:** `{rule['rule_type']}`")
            new_kws = st.text_input("Keywords (comma separated)", value=rule["keywords"])
            if st.form_submit_button("Update Priority Rule"):
                update_priority_keywords(rule["rule_type"], new_kws)
                setup_database.clear()
                setup_classifier.clear()
                st.success("Updated successfully!")
                st.rerun()

    st.markdown("---")
    st.subheader("2. Manage Categories")

    categories = get_all_categories_raw()
    df = pd.DataFrame(categories)
    st.dataframe(df, hide_index=True, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Add New Category")
        with st.form("add_cat_form"):
            new_name = st.text_input("Category Name (e.g. shipping)")
            new_kws = st.text_input("Keywords (comma separated)")
            new_team = st.text_input("Assigned Team (e.g. logistics-team)")
            if st.form_submit_button("Add Category"):
                if new_name and new_team:
                    try:
                        add_category(new_name, new_kws, new_team)
                        setup_database.clear()
                        setup_classifier.clear()
                        st.success("Category added!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("Name and Team are required.")

    with col2:
        st.markdown("#### Delete Category")
        with st.form("delete_cat_form"):
            del_name = st.selectbox(
                "Select Category to Delete", options=[c["name"] for c in categories]
            )
            if st.form_submit_button("Delete Category"):
                if del_name == "general":
                    st.error("Cannot delete the 'general' fallback category.")
                else:
                    delete_category(del_name)
                    setup_database.clear()
                    setup_classifier.clear()
                    st.success("Category deleted!")
                    st.rerun()


# ── Entry Point ───────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="Ticket Classification",
        page_icon="🚀",
        layout="wide",
    )
    load_css()

    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False

    rules = setup_database()

    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Dashboard", "Admin Panel"])

    if page == "Dashboard":
        render_dashboard(rules)
    elif page == "Admin Panel":
        if st.session_state.is_admin:
            render_admin_panel()
        else:
            render_admin_login()


if __name__ == "__main__":
    main()
