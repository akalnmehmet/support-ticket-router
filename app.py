import streamlit as st
import datetime
import random
import pandas as pd

from models.ticket import Ticket
from engine.evaluator import TicketEvaluator
from engine.router import TeamRouter
from database.db import (
    init_db, get_category_rules, get_team_mappings, get_priority_keywords,
    get_all_categories_raw, get_all_priority_rules_raw,
    add_category, update_category, delete_category, update_priority_keywords,
    get_recent_processed_tickets
)
from config.settings import ADMIN_PASSWORD

@st.cache_resource
def setup_database():
    init_db()
    return {
        "category_rules": get_category_rules(),
        "team_mapping": get_team_mappings(),
        "urgency_keywords": get_priority_keywords("urgency"),
        "billing_urgency_keywords": get_priority_keywords("billing_urgency")
    }

def render_dashboard(rules):
    st.title("Support Ticket Classification Engine")
    st.write("An intelligent, rule-based engine to categorize, prioritize, and route customer support tickets automatically.")

    # Load ticket history from DB (persists across page reloads)
    if "ticket_history" not in st.session_state:
        try:
            st.session_state.ticket_history = get_recent_processed_tickets(50)
        except Exception:
            st.session_state.ticket_history = []

    # Input Section
    with st.form("ticket_form", clear_on_submit=True):
        subject = st.text_input("Subject", placeholder="Brief summary of the issue...")
        message = st.text_area("Message", placeholder="Detailed explanation of the problem...", height=150)
        customer_type = st.selectbox("Customer Type", options=["Standard", "Premium"])
        
        submitted = st.form_submit_button("Process Ticket")

    # Processing Section
    if submitted:
        if not subject.strip() and not message.strip():
            st.warning("Please provide at least a subject or a message to process.")
        else:
            # Instantiate engine components
            evaluator = TicketEvaluator(rules["category_rules"], rules["urgency_keywords"], rules["billing_urgency_keywords"])
            router = TeamRouter(rules["team_mapping"])

            # Create a mock ticket ID and get current timestamp
            ticket_id = random.randint(10000, 99999)
            current_time = datetime.datetime.utcnow().isoformat() + "Z"

            # Instantiate Ticket object
            ticket = Ticket(
                id=ticket_id,
                subject=subject,
                message=message,
                customer_type=customer_type,
                created_at=current_time
            )

            # Evaluate and route
            with st.spinner("Analyzing ticket..."):
                category = evaluator.evaluate_category(ticket)
                priority = evaluator.evaluate_priority(ticket, category)
                team = router.route_ticket(category)
                reason = evaluator.generate_reason(ticket, category, priority)

            result = {
                "id": ticket_id,
                "subject": subject,
                "customer_type": customer_type,
                "category": category,
                "priority": priority,
                "team": team,
                "reason": reason,
                "timestamp": current_time
            }

            # Persist to DB and prepend to session (newest first)
            try:
                from database.db import save_processed_ticket
                save_processed_ticket(
                    {"id": ticket_id, "subject": subject, "message": message,
                     "customerType": customer_type},
                    {"category": category, "priority": priority,
                     "assignedTeam": team, "reason": reason}
                )
            except Exception:
                pass  # DB write failure should not crash the UI
            st.session_state.ticket_history.insert(0, result)

    # Display Results History
    if st.session_state.ticket_history:
        st.markdown("---")
        st.subheader("Classification Results History")
        
        for idx, item in enumerate(st.session_state.ticket_history):
            with st.expander(f"🎫 Ticket #{item['id']} | Priority: {item['priority'].upper()} | {item['category'].title()}", expanded=(idx == 0)):
                col1, col2, col3 = st.columns(3)
                
                col1.metric("📌 Category", item['category'].title())
                col2.metric("🔥 Priority", item['priority'].title())
                col3.metric("🏢 Assigned Team", item['team'].title().replace("-", " "))

                st.write(f"**Subject:** {item['subject']}")
                st.write(f"**Customer Type:** {item['customer_type']}")
                st.info(f"**🤖 AI Reasoning:** {item['reason']}")

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

def render_admin_panel():
    st.title("⚙️ Admin Panel")
    st.write("Manage ticket classification categories and priority keywords directly from the database.")
    
    if st.button("Logout"):
        st.session_state.is_admin = False
        st.rerun()

    st.markdown("---")
    st.subheader("1. Priority Keywords")
    priority_rules = get_all_priority_rules_raw()
    
    for rule in priority_rules:
        with st.form(f"form_priority_{rule['id']}"):
            st.write(f"**Rule Type:** `{rule['rule_type']}`")
            new_kws = st.text_input("Keywords (comma separated)", value=rule['keywords'])
            if st.form_submit_button("Update Priority Rule"):
                update_priority_keywords(rule['rule_type'], new_kws)
                setup_database.clear() # Clear cache to fetch new rules
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
                        st.success("Category added!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("Name and Team are required.")

    with col2:
        st.markdown("#### Delete Category")
        with st.form("delete_cat_form"):
            del_name = st.selectbox("Select Category to Delete", options=[c["name"] for c in categories])
            if st.form_submit_button("Delete Category"):
                if del_name == "general":
                    st.error("Cannot delete the 'general' fallback category.")
                else:
                    delete_category(del_name)
                    setup_database.clear()
                    st.success("Category deleted!")
                    st.rerun()

def main():
    st.set_page_config(page_title="Ticket Classification", page_icon="🚀", layout="wide")
    
    # Initialize session state for auth
    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False

    rules = setup_database()

    # Sidebar Navigation
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
