import os
import requests
import logging

logger = logging.getLogger(__name__)

def send_webhook(team_name: str, ticket_data: dict):
    """
    Sends a notification to a Slack/Discord webhook when a ticket is routed to a team.
    Looks for an environment variable WEBHOOK_<TEAM_NAME> or falls back to DISCORD_WEBHOOK_URL.
    """
    # Normalize team name for env var (e.g. payments-team -> WEBHOOK_PAYMENTS_TEAM)
    env_key = f"WEBHOOK_{team_name.upper().replace('-', '_')}"
    
    webhook_url = os.getenv(env_key)
    if not webhook_url:
        # Fallback to a general webhook URL
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        
    if not webhook_url:
        logger.info(f"No webhook URL configured for team '{team_name}'. Skipping notification.")
        return

    # Determine colors based on priority
    priority = ticket_data.get("priority", "low").lower()
    color = 3066993  # Default Green (Low)
    if priority == "high":
        color = 15158332  # Red
    elif priority == "medium":
        color = 16753920  # Orange

    # Construct Discord Webhook Payload (Embed)
    payload = {
        "content": f"🚨 **New Ticket Assigned to {team_name.replace('-', ' ').title()}!**",
        "embeds": [
            {
                "title": f"Ticket #{ticket_data.get('id', 'N/A')}: {ticket_data.get('subject', 'No Subject')}",
                "description": ticket_data.get("message", "No Message"),
                "color": color,
                "fields": [
                    {"name": "Category", "value": ticket_data.get("category", "General").title(), "inline": True},
                    {"name": "Priority", "value": priority.title(), "inline": True},
                    {"name": "Customer", "value": ticket_data.get("customerType", "Standard").title(), "inline": True},
                    {"name": "AI Reasoning", "value": ticket_data.get("reason", ""), "inline": False}
                ],
                "footer": {"text": "Support Ticket Router Engine"}
            }
        ]
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=5)
        if response.status_code in [200, 204]:
            logger.info(f"Successfully sent webhook notification to {team_name}.")
        else:
            logger.error(f"Failed to send webhook. Status Code: {response.status_code}, Response: {response.text}")
    except Exception as e:
        logger.error(f"Error sending webhook: {str(e)}")
