"""
SQLite-backed conversation state store for multi-turn interactions.
"""

import json
import os
import sqlite3
from datetime import datetime

from config.settings import DB_PATH


def _connect() -> sqlite3.Connection:
    """Get a connection, creating the DB directory if needed."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the conversations table if it doesn't exist."""
    conn = _connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            chat_id   INTEGER PRIMARY KEY,
            state     TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def get_state(chat_id: int) -> dict | None:
    """
    Retrieve the pending conversation state for a chat.

    Returns:
        State dict, or None if no pending state exists.
    """
    conn = _connect()
    row = conn.execute(
        "SELECT state FROM conversations WHERE chat_id = ?", (chat_id,),
    ).fetchone()
    conn.close()

    if row is None:
        return None

    state = json.loads(row["state"])
    # Return None for idle/empty states
    if not state or state.get("status") == "idle":
        return None
    return state


def set_state(chat_id: int, state: dict) -> None:
    """
    Save or update conversation state for a chat.

    Args:
        chat_id: Telegram chat ID.
        state: State dict to persist. Should include a "status" key.
    """
    conn = _connect()
    now = datetime.utcnow().isoformat()
    conn.execute(
        """
        INSERT INTO conversations (chat_id, state, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET state = ?, updated_at = ?
        """,
        (chat_id, json.dumps(state), now, json.dumps(state), now),
    )
    conn.commit()
    conn.close()


def clear_state(chat_id: int) -> None:
    """Clear the pending state for a chat (set to idle)."""
    set_state(chat_id, {"status": "idle"})
