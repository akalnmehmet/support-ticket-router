class TeamRouter:
    def __init__(self, team_mapping: dict):
        """Initialize the router with team mappings loaded from the database."""
        self.team_mapping = team_mapping

    def route_ticket(self, category: str) -> str:
        """
        Maps a given category to the corresponding support team.
        Returns 'general-support' as a fallback if the category is not found.
        """
        # Ensure input is lowercase and handle None safely
        category = (category or "").lower()
        return self.team_mapping.get(category, "general-support")
