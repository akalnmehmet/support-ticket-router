import json
import os

from models.ticket import Ticket, ProcessedTicket
from engine.evaluator import TicketEvaluator
from engine.router import TeamRouter

def main():
    input_file_path = "data/tickets.json"
    output_file_path = "data/processed_tickets.json"

    raw_tickets = []
    if os.path.exists(input_file_path):
        try:
            with open(input_file_path, 'r') as f:
                raw_tickets = json.load(f)
            print(f"Loaded {len(raw_tickets)} tickets from {input_file_path}")
        except Exception as e:
            print(f"Error reading {input_file_path}: {e}")
            return
    else:
        print(f"Error: '{input_file_path}' not found.")
        return

    evaluator = TicketEvaluator()
    router = TeamRouter()
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
            print(f"Skipping invalid ticket data: {t_data} (Error: {e})")

    # Print to console
    json_output = json.dumps(output_data, indent=2)
    print("\n--- Processed Tickets ---")
    print(json_output)

    # Write output to file
    try:
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
        with open(output_file_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        print(f"\nSuccessfully saved processed tickets to {output_file_path}")
    except Exception as e:
        print(f"\nFailed to save output to {output_file_path}: {e}")

if __name__ == "__main__":
    main()
