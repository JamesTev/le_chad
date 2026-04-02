# le Chad

A lightweight developer standup and task tracker. Track your team's daily standups, manage tasks across projects, and keep everyone on the same page.

## Features

- User accounts with login
- Project management (create, list, delete)
- Task tracking with priorities and assignees
- Comments on tasks
- Daily standup submissions
- Task search
- Basic stats dashboard
- CLI for quick access

## Quick start

```bash
# Install
uv sync

# Start the API server
uv run uvicorn le_chad.app:app --reload

# In another terminal, use the CLI
uv run le-chad tasks
uv run le-chad stats
uv run le-chad search "login"
uv run le-chad create "My new task" --description "Something to do"
```

## API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /users | Create a user |
| GET | /users | List all users |
| POST | /login | Log in |
| POST | /projects | Create a project |
| GET | /projects | List projects |
| DELETE | /projects/:id | Delete a project |
| POST | /tasks | Create a task |
| GET | /tasks | List all tasks |
| GET | /tasks/:id | Get task with comments |
| PUT | /tasks/:id | Update a task |
| DELETE | /tasks/:id | Delete a task |
| GET | /tasks/search | Search tasks |
| POST | /tasks/:id/comments | Add a comment |
| GET | /tasks/:id/comments | List comments |
| POST | /standups | Submit a standup |
| GET | /standups | List all standups |
| GET | /stats | Dashboard stats |

## Tech stack

- Python + FastAPI
- SQLite
- httpx (CLI)
