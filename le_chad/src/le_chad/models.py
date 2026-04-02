from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class Task(BaseModel):
    id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.TODO
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    search_score: Optional[float] = None


class SearchResult(BaseModel):
    task_id: str
    task_title: str
    task_description: str
    score: float
    
    class Config:
        from_attributes = True