import streamlit as st
import datetime
import random

from models.ticket import Ticket
from engine.evaluator import TicketEvaluator
from engine.router import TeamRouter

def main():
    st.set_page_config(page_title="Ticket Classification", page_icon="🚀", layout="centered")

    st.title("Support Ticket Classification Engine")
    st.write("An intelligent, rule-based engine to categorize, prioritize, and route customer support tickets automatically.")

    # Initialize session state for storing ticket history
    if "ticket_history" not in st.session_state:
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
            evaluator = TicketEvaluator()
            router = TeamRouter()

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

            # Add to history (newest first)
            st.session_state.ticket_history.insert(0, {
                "id": ticket_id,
                "subject": subject,
                "customer_type": customer_type,
                "category": category,
                "priority": priority,
                "team": team,
                "reason": reason,
                "timestamp": current_time
            })

    # Display Results History
    if st.session_state.ticket_history:
        st.markdown("---")
        st.subheader("Classification Results History")
        
        for idx, item in enumerate(st.session_state.ticket_history):
            # The most recent ticket is expanded by default, others are collapsed
            with st.expander(f"🎫 Ticket #{item['id']} | Priority: {item['priority'].upper()} | {item['category'].title()}", expanded=(idx == 0)):
                col1, col2, col3 = st.columns(3)
                
                col1.metric("📌 Category", item['category'].title())
                col2.metric("🔥 Priority", item['priority'].title())
                col3.metric("🏢 Assigned Team", item['team'].title().replace("-", " "))

                st.write(f"**Subject:** {item['subject']}")
                st.write(f"**Customer Type:** {item['customer_type']}")
                st.info(f"**🤖 AI Reasoning:** {item['reason']}")

if __name__ == "__main__":
    main()
