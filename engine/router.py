from config.rules import TEAM_ROUTING_RULES

class TeamRouter:
    """
    Handles the routing logic to assign support tickets to the appropriate team.
    """
    
    def route_ticket(self, category: str) -> str:
        """
        Determines the appropriate support team based on the ticket category.
        
        Args:
            category (str): The categorized issue type of the ticket.
            
        Returns:
            str: The name of the assigned team to handle the ticket. Defaults to 'general-support'.
        """
        return TEAM_ROUTING_RULES.get(category, "general-support")
