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
Given the user's message, current date/time, and timezone, extract a structured JSON object.

Return ONLY valid JSON — no markdown fences, no commentary.

Schema:
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
- For "update_event", populate "title" and "update_fields" with the changes.
- "recurrence_scope" should be "unspecified" unless the user clearly states "this one", "just this occurrence", "the whole series", "all of them", etc.
- If intent is unclear, use "unknown".
- Always return valid JSON.
"""


async def parse_intent(
    user_message: str,
    timezone: str | None = None,
) -> dict:
    """
    Parse a user's natural-language message into a structured intent dict.

    Args:
        user_message: The raw message from the user.
        timezone: Optional timezone override.

    Returns:
        Parsed intent dict. On failure, returns {"intent": "error", "reason": "..."}.
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
            # Remove first and last lines (fences)
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)

        intent = json.loads(cleaned)

        # Validate required field
        if "intent" not in intent:
            return {"intent": "error", "reason": "Missing 'intent' field in LLM output."}

        # Normalise optional fields
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

    except json.JSONDecodeError as e:
        logger.warning("Failed to parse Gemini response as JSON: %s", e)
        return {"intent": "error", "reason": f"Invalid JSON from LLM: {e}"}
    except RuntimeError as e:
        logger.error("Gemini API call failed: %s", e)
        return {"intent": "error", "reason": str(e)}
