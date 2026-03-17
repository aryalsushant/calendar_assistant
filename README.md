# Calendar Assistant Bot

A Telegram bot that manages your Google Calendar using natural language, powered by Gemini. Tell it what you want in plain English — it'll create, update, delete, and list your events.

> The bot understands recurring events. When you modify or delete one, it always asks whether you want to change just one occurrence or the entire series.

---

## Quick Setup

### Step 1 — Clone the repo

```bash
git clone https://github.com/aryalsushant/calendar_assistant.git
cd calendar_assistant
```

---

### Step 2 — Create a Telegram bot

1. Open Telegram and search for **@BotFather**.
2. Send `/newbot` and follow the prompts (choose a name and a username ending in `bot`).
3. BotFather will give you a token like `123456789:ABC-DEF...`. Copy it.

---

### Step 3 — Get a Gemini API key

1. Go to [Google AI Studio](https://aistudio.google.com/apikey) and sign in.
2. Click **Create API Key** and copy it.

---

### Step 4 — Set up Google Calendar API

#### 4a. Create a Google Cloud project

1. Go to [Google Cloud Console](https://console.cloud.google.com).
2. Click the project dropdown at the top → **New Project**.
3. Name it (e.g., `Calendar Assistant`) and click **Create**.
4. Make sure the new project is selected.

#### 4b. Enable the Calendar API

1. Go to **APIs & Services → Library** ([direct link](https://console.cloud.google.com/apis/library)).
2. Search for **Google Calendar API**, click it, then click **Enable**.

#### 4c. Configure the OAuth consent screen

1. Go to **APIs & Services → OAuth consent screen**.
2. Choose **External** → **Create**.
3. Fill in **App name** (e.g., `Calendar Assistant`), **User support email**, and **Developer contact email** — use your own email for all three.
4. Skip the logo — just scroll down and click **Save and Continue**.
5. On the **Scopes** page — don't change anything, just click **Save and Continue**.
6. On the **Test users** page — click **+ Add Users**, enter your Gmail address, then click **Save and Continue**.
7. Review the summary and click **Back to Dashboard**.

> While the app is in "Testing" mode, only test users you added can authorize it.

#### 4d. Create OAuth2 credentials

1. In the left sidebar, click **Credentials**.
2. Click **+ Create Credentials → OAuth client ID**.
3. Application type: **Desktop app**. Give it any name and click **Create**.
4. On the dialog that appears, click **Download JSON**.
5. Rename the downloaded file to `credentials.json` and move it into the project root (next to `main.py`).

---

### Step 5 — Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

| Variable | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token from Step 2 |
| `GEMINI_API_KEY` | Key from Step 3 |
| `GOOGLE_CREDENTIALS_PATH` | Path to your credentials file (default: `credentials.json`) |
| `GOOGLE_CALENDAR_ID` | Calendar to manage (default: `primary`) |

---

### Step 6 — Install and run

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

On the first run, a browser window opens for Google OAuth consent. Sign in and grant calendar access — a `token.json` is saved so you won't be asked again.

> If you see a "Google hasn't verified this app" warning, click **Advanced → Go to Calendar Assistant (unsafe)**. This is expected for personal OAuth apps in testing mode.

---

### Step 7 — Verify it's working

Check the terminal output. A healthy start looks like:

```
2026-03-16 20:30:00 - __main__ - INFO - Database initialized.
2026-03-16 20:30:00 - __main__ - INFO - Bot is starting... Press Ctrl+C to stop.
```

Then open your bot in Telegram and send a message like **"What's on my calendar tomorrow?"** — you should get a response listing your events.

---

## Example Commands

| What you say | What happens |
|---|---|
| "How does my schedule look tomorrow?" | Lists your events |
| "Schedule lunch with Alex Friday at 1pm" | Creates an event (asks for end time) |
| "Cancel my meeting with Bipul" | Finds and deletes the event |
| "Move my standup to Thursday at 3pm" | Updates the event time |

---

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

---

## Security

- **Never commit `.env`** — it contains your API tokens. The `.gitignore` excludes it automatically.
- **Never share `credentials.json` or `token.json`** — anyone with these can access your Google Calendar.
- Rotate your tokens immediately if you suspect they've been exposed.
