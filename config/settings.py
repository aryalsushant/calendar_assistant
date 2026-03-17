"""
Application configuration — loads all settings from .env file.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).resolve().parent.parent
load_dotenv(_project_root / ".env")

# ── Telegram ─────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

# ── Gemini ───────────────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")

# ── Google Calendar ──────────────────────────────────────────────────────────
GOOGLE_CREDENTIALS_PATH: str = os.getenv(
    "GOOGLE_CREDENTIALS_PATH",
    str(_project_root / "credentials.json"),
)
GOOGLE_TOKEN_PATH: str = str(_project_root / "token.json")
GOOGLE_CALENDAR_ID: str = os.getenv("GOOGLE_CALENDAR_ID", "primary")

# OAuth2 scopes needed for full calendar access
GOOGLE_SCOPES: list[str] = ["https://www.googleapis.com/auth/calendar"]

# ── Timezone ─────────────────────────────────────────────────────────────────
DEFAULT_TIMEZONE: str = "America/Chicago"

# ── Database ─────────────────────────────────────────────────────────────────
DB_PATH: str = str(_project_root / "data" / "conversation_state.db")
