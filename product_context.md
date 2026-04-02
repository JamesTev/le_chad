# Product Context: le Chad

## One-liner
A lightweight developer standup and task tracker for engineering teams to manage daily standups, tasks, and project collaboration.

## Tech Stack
- Python 3.14
- FastAPI 0.115+
- SQLite
- httpx 0.28+ (CLI)
- Pydantic (models)
- Uvicorn 0.34+ (server)

## Domain & User Persona
Developer productivity tool used by engineering teams to coordinate daily standups, track tasks with priorities and assignees, and maintain project visibility.

## Feature Inventory
- **User Management**: Account creation, login, user listing
- **Project Management**: Create/list/delete projects with owners
- **Task Tracking**: Create/read/update/delete tasks with status, priority, assignees
- **Comments**: Add/list comments on tasks
- **Standups**: Submit and view daily standup updates
- **Search**: Full-text search across tasks
- **Dashboard**: Basic stats (task counts, completion rates)
- **CLI**: Command-line interface for quick access to core features

## Architecture Notes
RESTful API built with FastAPI, SQLite for data persistence, single-file database with in-memory caching during startup. CLI uses httpx to interact with the API. No authentication middleware implemented despite JWT-like tokens being generated.

## Known Gaps & Pain Points
- **Security**: Plaintext password storage in database and login flow
- **SQL Injection**: Multiple raw SQL queries concatenate user input (login, search)
- **Performance**: N+1 query problem in task listing (comment counts)
- **Scalability**: SQLite not suitable for concurrent access
- **Notifications**: Synchronous sleep-based notifications with hardcoded delay
- **Data Integrity**: No foreign key constraints or cascading deletes
- **API Design**: No pagination controls in most endpoints
- **Error Handling**: Generic 500 errors without structured responses
- **Testing**: No test suite visible in codebase
- **Configuration**: Hardcoded secrets and URLs in config.py

## File Tree (relative paths for code changes)
- `le_chad/app.py` — FastAPI application with all endpoints
- `le_chad/db.py` — SQLite database layer (init, seed, queries)
- `le_chad/models.py` — Pydantic models (User, Task, Project, Comment, Standup)
- `le_chad/config.py` — Configuration constants (secrets, URLs, feature flags)
- `le_chad/cli.py` — httpx-based CLI client
- `le_chad/__init__.py` — Package init
- `pyproject.toml` — Project dependencies

## Discovery Keywords
- FastAPI standup tracker
- developer task management tool
- SQLite project management
- Python CLI productivity tool
- FastAPI SQLite REST API
- developer standup application
- task tracker with priorities
- engineering team collaboration tool
- FastAPI user authentication
- SQLite raw SQL injection vulnerability
- FastAPI Pydantic models
- developer productivity CLI
- FastAPI project management API
- SQLite memory leak
- FastAPI CORS configuration
- developer standup dashboard
- FastAPI pagination issues
- SQLite foreign key constraints
- FastAPI notification system
- developer team standup tool
- FastAPI comment system
- SQLite database performance
- FastAPI security best practices
- developer task search functionality