from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager

from models.ticket import Ticket as InternalTicket
from engine.evaluator import TicketEvaluator
from engine.router import TeamRouter
from database.db import init_db, get_category_rules, get_team_mappings, get_priority_keywords

# Pydantic Models for API (camelCase support for JSON Request/Response)
class ApiTicketRequest(BaseModel):
    id: int
    subject: str = ""
    message: str = ""
    customerType: str = Field(default="standard")
    createdAt: str = ""

class ApiTicketResponse(BaseModel):
    id: int
    category: str
    priority: str
    assignedTeam: str
    reason: str

# State dictionary to hold our engine singletons
engine_state = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    # Initialize DB and load rules into memory for fast processing
    init_db()
    category_rules = get_category_rules()
    team_mapping = get_team_mappings()
    urgency_keywords = get_priority_keywords("urgency")
    billing_urgency_keywords = get_priority_keywords("billing_urgency")

    # Instantiate the engines
    engine_state["evaluator"] = TicketEvaluator(category_rules, urgency_keywords, billing_urgency_keywords)
    engine_state["router"] = TeamRouter(team_mapping)
    
    yield # App is running
    
    # --- Shutdown ---
    engine_state.clear()

app = FastAPI(
    title="Support Ticket Router API",
    description="An intelligent engine to categorize, prioritize, and route customer support tickets automatically.",
    version="1.0.0",
    lifespan=lifespan
)

@app.post("/api/v1/process-ticket", response_model=ApiTicketResponse)
async def process_ticket(ticket_req: ApiTicketRequest):
    evaluator = engine_state.get("evaluator")
    router = engine_state.get("router")
    
    if not evaluator or not router:
        raise HTTPException(status_code=500, detail="Engine not initialized.")

    try:
        # Convert incoming API Request to Internal Domain Model
        internal_ticket = InternalTicket(
            id=ticket_req.id,
            subject=ticket_req.subject,
            message=ticket_req.message,
            customer_type=ticket_req.customerType,
            created_at=ticket_req.createdAt
        )

        # Execute Business Logic
        category = evaluator.evaluate_category(internal_ticket)
        priority = evaluator.evaluate_priority(internal_ticket, category)
        team = router.route_ticket(category)
        reason = evaluator.generate_reason(internal_ticket, category, priority)

        # Construct and return standard API Response
        return ApiTicketResponse(
            id=internal_ticket.id,
            category=category,
            priority=priority,
            assignedTeam=team,
            reason=reason
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing ticket: {str(e)}")
