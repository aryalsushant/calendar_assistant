"""
Intent parsing — extracts structured intent JSON from user messages via Gemini.
"""

import json
import logging

from llm.gemini_client import generate
from utils.datetime_utils import now_in_tz

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """\
You are an intent-extraction engine for a calendar assistant.
Given the user's message, current date/time, and timezone, extract structured JSON.

Return ONLY valid JSON — no markdown fences, no commentary.

IMPORTANT: If the user's message contains MULTIPLE actions (e.g. "Move my standup to 3pm and cancel my meeting with Bipul"), return a JSON ARRAY of intent objects. If the message contains only ONE action, return a single JSON object (not an array).

Each intent object follows this schema:
{
  "intent": "get_schedule" | "create_event" | "delete_event" | "update_event" | "unknown",
  "title": "<event title or search phrase, or null>",
  "datetime": "<ISO 8601 datetime string for the event, or null>",
  "end_datetime": "<ISO 8601 datetime string for the event end, or null>",
  "time_range": "<natural language range like 'next 2 days', or null>",
  "recurrence_scope": "single" | "series" | "unspecified",
  "attendees": ["<email addresses if user wants to invite someone, otherwise empty list>"],
  "timezone": "<IANA timezone if user specifies one, otherwise null>",
  "update_fields": {
    "new_datetime": "<new ISO 8601 datetime if moving event, or null>",
    "new_end_datetime": "<new end datetime if changing duration, or null>",
    "new_title": "<new title if renaming, or null>"
  },
  "extra": {}
}

Rules:
- For "get_schedule", populate "time_range" (e.g. "next 2 days", "tomorrow", "this week").
- For "create_event", populate "title", "datetime". Populate "end_datetime" ONLY if the user specifies an end time or duration. If NOT specified, set "end_datetime" to null.
- For "delete_event", populate "title" and optionally "datetime" to help narrow the search.
- For "update_event", populate "title", "datetime" (the current date/time of the event being changed), and "update_fields" with the changes.
- IMPORTANT — recurrence_scope rules:
  - If the user mentions a SPECIFIC DATE (e.g. "tomorrow", "Friday", "March 20th"), set recurrence_scope to "single". They mean that one occurrence.
  - If the user explicitly says "all", "every", "the whole series", "all occurrences", set to "series".
  - ONLY set to "unspecified" if the user references a recurring event WITHOUT any date AND without indicating single vs series (e.g. "cancel my weekly standup" with no date).
- "datetime" should ALWAYS be populated when the user references a date, even for delete/update intents. This is critical for narrowing the search.
- If intent is unclear, use "unknown".
- Always return valid JSON.
"""


def _normalise_intent(intent: dict) -> dict:
    """Fill in default values for optional fields."""
    intent.setdefault("title", None)
    intent.setdefault("datetime", None)
    intent.setdefault("end_datetime", None)
    intent.setdefault("time_range", None)
    intent.setdefault("recurrence_scope", "unspecified")
    intent.setdefault("attendees", [])
    intent.setdefault("timezone", None)
    intent.setdefault("update_fields", {})
    intent.setdefault("extra", {})
    return intent


async def parse_intent(
    user_message: str,
    timezone: str | None = None,
) -> list[dict]:
    """
    Parse a user's natural-language message into a list of structured intents.

    Returns a list even for single-action messages (for uniform handling).
    On failure, returns a single-element list with an error intent.
    """
    tz = timezone or "America/Chicago"
    now = now_in_tz(tz)

    prompt = (
        f"Current date/time: {now.isoformat()}\n"
        f"Timezone: {tz}\n\n"
        f"User message: {user_message}"
    )

    try:
        raw = await generate(prompt, system_instruction=SYSTEM_INSTRUCTION)

        # Strip markdown fences if model wraps output
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)

        parsed = json.loads(cleaned)

        # Normalise to a list of intents
        if isinstance(parsed, list):
            intents = parsed
        elif isinstance(parsed, dict):
            intents = [parsed]
        else:
            return [{"intent": "error", "reason": "Unexpected LLM output format."}]

        # Validate and normalise each intent
        result = []
        for intent in intents:
            if not isinstance(intent, dict) or "intent" not in intent:
                logger.warning("Skipping invalid intent object: %s", intent)
                continue
            result.append(_normalise_intent(intent))

        if not result:
            return [{"intent": "error", "reason": "No valid intents parsed."}]

        return result

    except json.JSONDecodeError as e:
        logger.warning("Failed to parse Gemini response as JSON: %s", e)
        return [{"intent": "error", "reason": f"Invalid JSON from LLM: {e}"}]
    except RuntimeError as e:
        logger.error("Gemini API call failed: %s", e)
        return [{"intent": "error", "reason": str(e)}]
