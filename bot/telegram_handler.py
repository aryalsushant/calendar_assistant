"""
Telegram bot handler — registers commands and routes messages.
"""

import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from bot.message_router import handle_message

logger = logging.getLogger(__name__)


async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    await update.message.reply_text(
        "👋 Hey! I'm your calendar assistant.\n\n"
        "Ask me things like:\n"
        "• \"How does my schedule look for tomorrow?\"\n"
        "• \"Schedule lunch with Alex tomorrow at 1pm\"\n"
        "• \"Cancel my meeting with Bipul\"\n"
        "• \"Move my standup to Friday at 3pm\"\n\n"
        "Just message me in plain English!"
    )


async def _help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await update.message.reply_text(
        "Here's what I can do:\n\n"
        "📅 Check schedule — \"What's on my calendar this week?\"\n"
        "➕ Create events — \"Schedule a dentist appointment Friday at 9am\"\n"
        "✏️ Update events — \"Move my 1-on-1 to Thursday at 2pm\"\n"
        "❌ Cancel events — \"Cancel my meeting with Sarah tomorrow\"\n\n"
        "I'll ask for clarification if anything is unclear!"
    )


async def _handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route all text messages through the message router."""
    chat_id = update.effective_chat.id
    text = update.message.text

    logger.info("Message from %s: %s", chat_id, text)

    # Show typing indicator while processing
    await update.effective_chat.send_action("typing")

    response = await handle_message(chat_id, text)
    await update.message.reply_text(response)


def create_application(token: str) -> Application:
    """
    Build and configure the Telegram bot application.

    Args:
        token: Telegram bot token from BotFather.

    Returns:
        Configured Application ready to be started.
    """
    app = Application.builder().token(token).build()

    # Command handlers
    app.add_handler(CommandHandler("start", _start))
    app.add_handler(CommandHandler("help", _help))

    # Text message handler (catches everything else)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_text))

    return app
