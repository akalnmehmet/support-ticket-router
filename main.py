import json
import os
import logging

from models.ticket import Ticket, ProcessedTicket
from engine.evaluator import TicketEvaluator
from engine.router import TeamRouter
from database.db import init_db, get_category_rules, get_team_mappings, get_priority_keywords

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main(input_file_path="data/tickets.json", output_file_path="data/processed_tickets.json"):

    raw_tickets = []
    if os.path.exists(input_file_path):
        try:
            with open(input_file_path, 'r', encoding="utf-8") as f:
                raw_tickets = json.load(f)
            logger.info(f"Loaded {len(raw_tickets)} tickets from {input_file_path}")
        except Exception as e:
            logger.error(f"Error reading {input_file_path}: {e}")
            return
    else:
        logger.error(f"Error: '{input_file_path}' not found.")
        return

    # Initialize DB and Load Rules
    init_db()
    category_rules = get_category_rules()
    team_mapping = get_team_mappings()
    urgency_keywords = get_priority_keywords("urgency")
    billing_urgency_keywords = get_priority_keywords("billing_urgency")

    evaluator = TicketEvaluator(category_rules, urgency_keywords, billing_urgency_keywords)
    router = TeamRouter(team_mapping)
    output_data = []

    for t_data in raw_tickets:
        try:
            # Map camelCase JSON input to snake_case Python dataclass fields
            ticket = Ticket(
                id=t_data.get("id"),
                subject=t_data.get("subject", ""),
                message=t_data.get("message", ""),
                customer_type=t_data.get("customerType", "standard"),
                created_at=t_data.get("createdAt", "")
            )
            
            # Process Logic
            category = evaluator.evaluate_category(ticket)
            priority = evaluator.evaluate_priority(ticket, category)
            team = router.route_ticket(category)
            reason = evaluator.generate_reason(ticket, category, priority)
            
            # Create ProcessedTicket object internally
            pt = ProcessedTicket(
                id=ticket.id,
                category=category,
                priority=priority,
                assigned_team=team,
                reason=reason
            )
            
            # Map Python snake_case back to expected camelCase JSON output
            output_data.append({
                "id": pt.id,
                "category": pt.category,
                "priority": pt.priority,
                "assignedTeam": pt.assigned_team,
                "reason": pt.reason
            })
            
        except Exception as e:
            logger.warning(f"Skipping invalid ticket data: {t_data} (Error: {e})")

    # Print to console normally for CLI pipeline processing
    json_output = json.dumps(output_data, indent=2)
    print("\n--- Processed Tickets ---")
    print(json_output)

    # Write output to file
    try:
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
        with open(output_file_path, 'w', encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)
        logger.info(f"Successfully saved processed tickets to {output_file_path}")
    except Exception as e:
        logger.error(f"Failed to save output to {output_file_path}: {e}")

if __name__ == "__main__":
    main()
