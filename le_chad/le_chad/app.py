import time

from fastapi import FastAPI
from le_chad.config import DEBUG, SECRET_KEY, NOTIFICATION_DELAY
from le_chad.db import get_connection, init_db, seed_data
from le_chad.models import (
    UserCreate,
    TaskCreate,
    TaskUpdate,
    CommentCreate,
    StandupCreate,
    ProjectCreate,
)

app = FastAPI(title="le Chad", debug=DEBUG)


@app.on_event("startup")
def startup():
    init_db()
    seed_data()


# ---- Users ----


@app.post("/users")
def create_user(user: UserCreate):
    conn = get_connection()
    c = conn.cursor()
    # stores password in plaintext
    c.execute(
        "INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
        (user.username, user.password, user.email),
    )
    conn.commit()
    uid = c.lastrowid
    conn.close()
    return {"id": uid, "username": user.username}


@app.get("/users")
def list_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    rows = c.fetchall()
    conn.close()
    users = []
    for r in rows:
        users.append(
            {"id": r[0], "username": r[1], "password": r[2], "email": r[3], "created_at": r[4]}
        )
    return users


@app.post("/login")
def login(username: str, password: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM users WHERE username = '" + username + "' AND password = '" + password + "'"
    )
    user = c.fetchone()
    conn.close()
    if user:
        return {"token": SECRET_KEY + "_" + str(user[0]), "user_id": user[0]}
    return {"error": "bad credentials"}


# ---- Projects ----


@app.post("/projects")
def create_project(project: ProjectCreate):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO projects (name, description, owner) VALUES (?, ?, ?)",
        (project.name, project.description, project.owner),
    )
    conn.commit()
    pid = c.lastrowid
    conn.close()
    return {"id": pid, "name": project.name}


@app.get("/projects")
def list_projects():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM projects")
    rows = c.fetchall()
    conn.close()
    return [
        {"id": r[0], "name": r[1], "description": r[2], "owner": r[3], "created_at": r[4]}
        for r in rows
    ]


@app.delete("/projects/{project_id}")
def delete_project(project_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    return {"deleted": True}


# ---- Tasks ----


@app.post("/tasks")
def create_task(task: TaskCreate):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO tasks (title, description, status, assignee, priority) VALUES (?, ?, ?, ?, ?)",
        (task.title, task.description, task.status, task.assignee, task.priority),
    )
    conn.commit()
    tid = c.lastrowid
    conn.close()

    _send_notification(task.assignee, f"You were assigned task: {task.title}")

    return {"id": tid, "title": task.title, "status": task.status}


@app.get("/tasks")
def list_tasks(page: int = 1, limit: int = 10):
    conn = get_connection()
    c = conn.cursor()
    offset = (page - 1) * limit
    c.execute("SELECT * FROM tasks LIMIT ? OFFSET ?", (limit, offset))
    rows = c.fetchall()

    tasks = []
    for r in rows:
        # N+1: fetch comment count per task
        c2 = conn.cursor()
        c2.execute("SELECT COUNT(*) FROM comments WHERE task_id = ?", (r[0],))
        count = c2.fetchone()[0]
        tasks.append({
            "id": r[0],
            "title": r[1],
            "description": r[2],
            "status": r[3],
            "assignee": r[4],
            "priority": r[5],
            "project_id": r[6],
            "created_at": r[7],
            "comment_count": count,
        })

    conn.close()
    return tasks


@app.get("/tasks/search")
def search_tasks(q: str = ""):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM tasks WHERE title LIKE '%" + q + "%' OR description LIKE '%" + q + "%'")
    rows = c.fetchall()
    conn.close()
    results = []
    for r in rows:
        results.append(dict(id=r[0], title=r[1], description=r[2], status=r[3]))
    return results


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    r = c.fetchone()
    if not r:
        conn.close()
        return {"error": "not found"}

    c.execute("SELECT * FROM comments WHERE task_id = ?", (task_id,))
    comments = c.fetchall()
    conn.close()

    comment_list = []
    for cm in comments:
        comment_list.append(
            {"id": cm[0], "task_id": cm[1], "body": cm[2], "author": cm[3], "created_at": cm[4]}
        )

    return {
        "id": r[0],
        "title": r[1],
        "description": r[2],
        "status": r[3],
        "assignee": r[4],
        "priority": r[5],
        "project_id": r[6],
        "created_at": r[7],
        "comments": comment_list,
    }


@app.put("/tasks/{task_id}")
def update_task(task_id: int, task: TaskUpdate):
    conn = get_connection()
    c = conn.cursor()

    fields = []
    values = []
    if task.title is not None:
        fields.append("title = ?")
        values.append(task.title)
    if task.description is not None:
        fields.append("description = ?")
        values.append(task.description)
    if task.status is not None:
        fields.append("status = ?")
        values.append(task.status)
    if task.assignee is not None:
        fields.append("assignee = ?")
        values.append(task.assignee)
    if task.priority is not None:
        fields.append("priority = ?")
        values.append(task.priority)

    if not fields:
        conn.close()
        return {"error": "nothing to update"}

    values.append(task_id)
    query = f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?"
    c.execute(query, values)
    conn.commit()
    conn.close()

    if task.assignee:
        _send_notification(task.assignee, f"You were assigned task #{task_id}")

    return {"updated": True}


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return {"deleted": True}


# ---- Comments ----


@app.post("/tasks/{task_id}/comments")
def add_comment(task_id: int, comment: CommentCreate):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO comments (task_id, body, author) VALUES (?, ?, ?)",
        (task_id, comment.body, comment.author),
    )
    conn.commit()
    cid = c.lastrowid
    conn.close()
    return {"id": cid}


@app.get("/tasks/{task_id}/comments")
def list_comments(task_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM comments WHERE task_id = ?", (task_id,))
    rows = c.fetchall()
    conn.close()
    return [
        {"id": r[0], "task_id": r[1], "body": r[2], "author": r[3], "created_at": r[4]}
        for r in rows
    ]


# ---- Standups ----


@app.post("/standups")
def create_standup(standup: StandupCreate):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO standups (user, yesterday, today, blockers) VALUES (?, ?, ?, ?)",
        (standup.user, standup.yesterday, standup.today, standup.blockers),
    )
    conn.commit()
    sid = c.lastrowid
    conn.close()
    return {"id": sid}


@app.get("/standups")
def list_standups():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM standups")
    rows = c.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "user": r[1],
            "yesterday": r[2],
            "today": r[3],
            "blockers": r[4],
            "created_at": r[5],
        }
        for r in rows
    ]


# ---- Stats ----


@app.get("/stats")
def get_stats():
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM tasks")
    total = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM tasks WHERE status = 'open'")
    open_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM tasks WHERE status = 'done'")
    done_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM users")
    user_count = c.fetchone()[0]

    conn.close()
    return {
        "total_tasks": total,
        "open_tasks": open_count,
        "done_tasks": done_count,
        "completion_rate": done_count / total,
        "users": user_count,
    }


# ---- Helpers ----


def _send_notification(user, message):
    if not user:
        return
    print(f"Sending notification to {user}: {message}")
    time.sleep(NOTIFICATION_DELAY)
    print("Notification sent")