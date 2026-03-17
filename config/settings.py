"""
Application configuration — loads all settings from .env file.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).resolve().parent.parent
load_dotenv(_project_root / ".env")


def _require(name: str) -> str:
    """Fetch a required env var, raising an error if it's missing."""
    value = os.getenv(name)
    if not value:
        raise EnvironmentError(f"Missing required environment variable: {name}")
    return value


# ── Telegram ─────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN: str = _require("TELEGRAM_BOT_TOKEN")

# ── Gemini ───────────────────────────────────────────────────────────────────
GEMINI_API_KEY: str = _require("GEMINI_API_KEY")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

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
DEFAULT_TIMEZONE: str = os.getenv("TIMEZONE", "America/Chicago")

# ── Database ─────────────────────────────────────────────────────────────────
DB_PATH: str = str(_project_root / "data" / "conversation_state.db")
