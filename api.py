from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from worker import process_ticket_task, celery_app
from database.db import init_db
# All env vars are sourced from config.settings (via database.db and worker modules)

# ─── Rate Limiter ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ─── Pydantic Request / Response Models ───────────────────────────────────────
class ApiTicketRequest(BaseModel):
    id: int
    subject: str = ""
    message: str = ""
    customerType: str = Field(default="standard")
    createdAt: str = ""

    @field_validator("subject", "message", mode="before")
    @classmethod
    def strip_whitespace(cls, v):
        return (v or "").strip()

class TaskResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[dict] = None

# ─── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

# ─── App Factory ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Support Ticket Router API",
    description=(
        "Asynchronous engine to categorize, prioritize, and route "
        "customer support tickets using Celery & Redis."
    ),
    version="1.0.0",  # API contract is v1; matches /api/v1/ URL prefix
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ─── Endpoints ────────────────────────────────────────────────────────────────
@app.post("/api/v1/process-ticket", response_model=TaskResponse)
@limiter.limit("30/minute")
async def process_ticket(request: Request, ticket_req: ApiTicketRequest):
    """
    Submits a support ticket to the message queue for async classification.

    Rate limit: 30 requests / minute per IP.
    """
    try:
        task = process_ticket_task.delay(ticket_req.model_dump())
        return TaskResponse(task_id=task.id, status="PENDING")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enqueue task: {str(e)}")


@app.get("/api/v1/task/{task_id}", response_model=TaskResponse)
@limiter.limit("120/minute")
async def get_task_status(request: Request, task_id: str):
    """
    Polls the status and result of a previously submitted ticket task.

    Rate limit: 120 requests / minute per IP.
    """
    task = celery_app.AsyncResult(task_id)
    return TaskResponse(
        task_id=task_id,
        status=task.status,
        result=task.result if task.ready() else None
    )


@app.get("/health")
async def health_check():
    """Simple liveness check endpoint."""
    return {"status": "ok", "version": "1.0.0"}

