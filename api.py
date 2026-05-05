from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from worker import process_ticket_task, celery_app
from database.db import init_db

# Pydantic Models for API
class ApiTicketRequest(BaseModel):
    id: int
    subject: str = ""
    message: str = ""
    customerType: str = Field(default="standard")
    createdAt: str = ""

class TaskResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[dict] = None

app = FastAPI(
    title="Support Ticket Router API (Async)",
    description="Asynchronous engine to categorize, prioritize, and route customer support tickets using Celery & Redis.",
    version="2.0.0"
)

@app.on_event("startup")
async def startup_event():
    # Ensure database schema exists before taking requests
    init_db()

@app.post("/api/v1/process-ticket", response_model=TaskResponse)
async def process_ticket(ticket_req: ApiTicketRequest):
    """Submits a ticket to the Redis message queue for asynchronous processing."""
    try:
        # Enqueue the task
        # .dict() handles camelCase keys via alias or as defined
        task = process_ticket_task.delay(ticket_req.model_dump())
        
        return TaskResponse(
            task_id=task.id,
            status="PENDING"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enqueue task: {str(e)}")

@app.get("/api/v1/task/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str):
    """Retrieves the status and result of an asynchronously processed ticket."""
    task = celery_app.AsyncResult(task_id)
    
    response = {
        "task_id": task_id,
        "status": task.status,
        "result": task.result if task.ready() else None
    }
    
    return TaskResponse(**response)
