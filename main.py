"""
Entry point — initializes the database and starts the Telegram bot.
"""

import logging
import sys

from bot.state_store import init_db
from bot.telegram_handler import create_application
from config.settings import TELEGRAM_BOT_TOKEN

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Start the calendar assistant bot."""
    # Validate token
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set. Please check your .env file.")
        sys.exit(1)

    # Initialize SQLite conversation store
    init_db()
    logger.info("Database initialized.")

    # Build and run the Telegram bot
    app = create_application(TELEGRAM_BOT_TOKEN)
    logger.info("Bot is starting... Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
