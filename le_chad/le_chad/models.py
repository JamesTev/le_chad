from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    password: str
    email: str


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    status: str = "open"
    assignee: str = None
    priority: str = "medium"


class TaskUpdate(BaseModel):
    title: str = None
    description: str = None
    status: str = None
    assignee: str = None
    priority: str = None


class CommentCreate(BaseModel):
    body: str
    author: str


class StandupCreate(BaseModel):
    user: str
    yesterday: str
    today: str
    blockers: str = ""


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    owner: str = None
