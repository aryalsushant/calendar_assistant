# Calendar Assistant Bot

A Telegram bot that manages your Google Calendar using natural language, powered by Gemini.

**Architecture:**
```
Telegram → Python bot → Gemini (intent) → Calendar API → Gemini (response) → Telegram
```

## Setup

### 1. Google Cloud Console
1. Create a project at [console.cloud.google.com](https://console.cloud.google.com)
2. Enable the **Google Calendar API**
3. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
4. Choose **Desktop application**, download the JSON, and save it as `credentials.json` in the project root

### 2. Telegram Bot
1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot`, follow the prompts, and copy the token

### 3. Gemini API
1. Get an API key from [Google AI Studio](https://aistudio.google.com/apikey)

### 4. Environment
```bash
cp .env.example .env
# Fill in your values:
#   TELEGRAM_BOT_TOKEN=...
#   GEMINI_API_KEY=...
#   GOOGLE_CREDENTIALS_PATH=credentials.json
```

### 5. Install & Run
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

On first run, a browser window will open for Google OAuth consent. After granting access, a `token.json` is saved for future runs.

## Example Commands

| What you say | What happens |
|---|---|
| "How does my schedule look tomorrow?" | Lists your events |
| "Schedule lunch with Alex Friday at 1pm" | Creates an event (asks for end time) |
| "Cancel my meeting with Bipul" | Finds and deletes the event |
| "Move my standup to Thursday at 3pm" | Updates the event time |

The bot handles **recurring events** — it will always ask whether you want to change just one occurrence or the entire series before making changes.

## Project Structure

```
├── bot/
│   ├── telegram_handler.py   # Telegram command & message handlers
│   ├── message_router.py     # Core orchestration logic
│   └── state_store.py        # SQLite conversation state
├── llm/
│   ├── gemini_client.py      # Gemini API wrapper
│   ├── intent_parser.py      # NL → structured intent JSON
│   └── response_generator.py # Structured data → natural response
├── gcal/
│   ├── google_client.py      # OAuth2 & Calendar service
│   └── event_service.py      # CRUD + recurrence helpers
├── utils/
│   ├── datetime_utils.py     # Date parsing & formatting
│   └── fuzzy_match.py        # Fuzzy event matching
├── config/
│   └── settings.py           # Environment config
└── main.py                   # Entry point
```
