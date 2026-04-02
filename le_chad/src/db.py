import sqlite3
from typing import Optional

def init_db(db_path: str) -> sqlite3.Connection:
    """Initialize the database connection and enable foreign key constraints."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def get_db_connection(db_path: str) -> sqlite3.Connection:
    """Get a database connection with foreign key constraints enabled."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn