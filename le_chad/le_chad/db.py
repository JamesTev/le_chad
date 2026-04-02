import sqlite3
import math
from le_chad.config import DATABASE_URL

_warm_cache = []


def get_connection():
    return sqlite3.connect(DATABASE_URL)


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT,
            email TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            owner TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            status TEXT DEFAULT 'open',
            assignee TEXT,
            priority TEXT DEFAULT 'medium',
            project_id INTEGER,
            embedding BLOB,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            body TEXT,
            author TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS standups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            yesterday TEXT,
            today TEXT,
            blockers TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

    _warm_up_cache()


def _warm_up_cache():
    global _warm_cache
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM tasks")
        _warm_cache = c.fetchall()
    except:
        pass
    conn.close()


def seed_data():
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] > 0:
        conn.close()
        return

    users = [
        ("alice", "password123", "alice@lechad.io"),
        ("bob", "password123", "bob@lechad.io"),
        ("charlie", "qwerty", "charlie@lechad.io"),
        ("admin", "admin123", "admin@lechad.io"),
    ]
    for u in users:
        c.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)", u)

    projects = [
        ("Backend API", "Core REST API for le Chad", "alice"),
        ("Frontend", "React dashboard", "bob"),
        ("Mobile App", "iOS and Android app", "charlie"),
        ("DevOps", "CI/CD and infrastructure", "alice"),
    ]
    for p in projects:
        c.execute("INSERT INTO projects (name, description, owner) VALUES (?, ?, ?)", p)

    tasks = [
        ("Fix login timeout", "Users report being logged out after 5 minutes", "open", "alice", "high", 1, None),
        ("Add password reset", "No way to reset password currently", "open", "bob", "high", 1, None),
        ("Dashboard loading slow", "Takes 10+ seconds to load task list", "open", "bob", "critical", 2, None),
        ("Search is broken", "Search returns no results for exact matches", "open", "alice", "high", 1, None),
        ("Add dark mode", "Multiple user requests for dark mode", "open", "charlie", "medium", 2, None),
        ("Fix mobile layout", "Buttons overlap on small screens", "open", "charlie", "high", 3, None),
        ("Add CSV export", "Users want to export their tasks", "open", None, "medium", 1, None),
        ("Rate limiting", "No rate limiting on API endpoints", "open", "alice", "high", 1, None),
        ("Fix duplicate users", "Can create multiple users with same username", "open", "alice", "critical", 1, None),
        ("Add task due dates", "Tasks have no due date field", "open", None, "medium", 1, None),
        ("Improve error messages", "API returns generic 500 errors", "in_progress", "bob", "medium", 1, None),
        ("Add user avatars", "Profile pictures for users", "open", None, "low", 2, None),
        ("Fix comment count", "Task list shows wrong number of comments", "open", "alice", "medium", 1, None),
        ("Add task labels", "Users want to tag tasks with labels", "open", None, "medium", 1, None),
        ("Setup CI/CD", "No automated testing or deployment", "open", "alice", "high", 4, None),
        ("Fix pagination", "Page 2 shows same results as page 1", "open", "bob", "high", 1, None),
        ("Add email notifications", "No notifications when assigned to task", "open", None, "medium", 1, None),
        ("Fix timezone handling", "All dates show in UTC regardless of user timezone", "open", "bob", "medium", 1, None),
        ("Add task attachments", "Users want to attach files to tasks", "open", None, "low", 1, None),
        ("Improve API docs", "Swagger docs are incomplete", "open", None, "low", 1, None),
        ("Fix standup date filter", "Cannot filter standups by date range", "open", "alice", "medium", 1, None),
        ("Add project archiving", "No way to archive completed projects", "open", None, "low", 1, None),
        ("Fix memory leak", "Server memory usage grows over time", "open", "alice", "critical", 4, None),
        ("Add bulk task update", "Cannot update multiple tasks at once", "open", None, "medium", 1, None),
        ("Fix CORS errors", "Frontend gets CORS errors on every request", "open", "bob", "high", 2, None),
        ("Add activity feed", "No way to see recent changes", "open", None, "low", 2, None),
        ("Fix delete cascade", "Deleting a project leaves orphaned tasks", "open", "alice", "high", 1, None),
        ("Add task priorities", "Need visual indicators for task priority", "in_progress", "charlie", "medium", 2, None),
        ("Fix standup submission", "Standup fails silently with empty blockers", "open", "bob", "medium", 1, None),
        ("Add webhook support", "Integrate with Slack/Discord for notifications", "open", None, "medium", 1, None),
    ]
    for t in tasks:
        c.execute(
            "INSERT INTO tasks (title, description, status, assignee, priority, project_id, embedding) VALUES (?, ?, ?, ?, ?, ?, ?)",
            t,
        )

    comments = [
        (1, "This is really annoying, happens every day", "bob"),
        (1, "Same here, I keep losing my session", "charlie"),
        (3, "Confirmed, dashboard is unusable with 100+ tasks", "alice"),
        (3, "This is our #1 user complaint right now", "bob"),
        (4, "I think this is related to the SQL query in search endpoint", "alice"),
        (9, "This is a security issue, should be critical", "alice"),
        (9, "Agreed, someone could impersonate another user", "bob"),
        (16, "Blocking my workflow, I have 200+ tasks and can't navigate", "charlie"),
        (23, "Server crashed twice this week due to this", "alice"),
        (25, "Frontend team is completely blocked by this", "bob"),
    ]
    for cm in comments:
        c.execute("INSERT INTO comments (task_id, body, author) VALUES (?, ?, ?)", cm)

    standups = [
        ("alice", "Fixed auth bug", "Working on search", "Blocked by DB performance"),
        ("bob", "Dashboard redesign", "Pagination fix", ""),
        ("charlie", "Mobile layout fixes", "Dark mode research", "Need design specs"),
    ]
    for s in standups:
        c.execute("INSERT INTO standups (user, yesterday, today, blockers) VALUES (?, ?, ?, ?)", s)

    conn.commit()
    conn.close()


def search_tasks_by_embedding(query_embedding: list[float], limit: int = 10) -> list:
    conn = get_connection()
    c = conn.cursor()
    
    # Convert embedding to bytes for storage
    query_embedding_bytes = bytes([int(x * 255) for x in query_embedding])
    
    # Calculate cosine similarity and rank tasks
    c.execute("""
        SELECT id, title, description, status, assignee, priority, project_id, embedding,
               (1 - (embedding <-> ?)) as similarity
        FROM tasks
        ORDER BY similarity DESC
        LIMIT ?
    """, (query_embedding_bytes, limit))
    
    results = c.fetchall()
    conn.close()
    return results


def search_tasks(query: str = None, use_embeddings: bool = False, query_embedding: list[float] = None, limit: int = 10) -> list:
    conn = get_connection()
    c = conn.cursor()

    if use_embeddings and query_embedding is not None:
        return search_tasks_by_embedding(query_embedding, limit)
    
    if not query:
        c.execute("SELECT * FROM tasks LIMIT ?", (limit,))
    else:
        search_term = f"%{query}%"
        c.execute("""
            SELECT * FROM tasks
            WHERE title LIKE ? OR description LIKE ?
            LIMIT ?
        """, (search_term, search_term, limit))

    results = c.fetchall()
    conn.close()
    return results