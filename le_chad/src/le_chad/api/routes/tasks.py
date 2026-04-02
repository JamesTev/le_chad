from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel

from le_chad.api.dependencies import get_task_service
from le_chad.services.task_service import TaskService
from le_chad.models.task import Task, SearchResult

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskSearchRequest(BaseModel):
    query: str
    limit: int = 10


class TaskSearchResponse(BaseModel):
    results: List[SearchResult]
    total: int


@router.post("/search", response_model=TaskSearchResponse)
async def search_tasks(
    request: TaskSearchRequest,
    task_service: TaskService = Depends(get_task_service),
):
    """Search tasks using BM25 scoring."""
    try:
        results, total = task_service.search_tasks(
            query=request.query, limit=request.limit
        )
        return TaskSearchResponse(results=results, total=total)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))