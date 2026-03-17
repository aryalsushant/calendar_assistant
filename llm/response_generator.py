"""
Natural-language response generation via Gemini.
"""

from llm.gemini_client import generate

SYSTEM_INSTRUCTION = """\
You are a friendly calendar assistant. Generate concise, natural, human-like responses.
Keep replies short — one or two sentences max unless listing a schedule.
Do NOT use markdown formatting. Use plain text only.
Do NOT repeat information the user already knows.
Sound like a helpful human, not a robot.
"""


async def generate_response(action_result: dict, context: str = "") -> str:
    """
    Generate a human-friendly response based on an action result.

    Args:
        action_result: Dict describing what happened, e.g.:
            {"action": "created", "summary": "Lunch with Alex",
             "start": "Monday at 1:00 PM", "end": "Monday at 2:00 PM"}
        context: Optional extra context for the model.

    Returns:
        Natural-language response string.
    """
    prompt = (
        f"Action result: {action_result}\n"
        f"Context: {context}\n\n"
        "Generate a brief, friendly confirmation or informational message for the user."
    )
    return await generate(prompt, system_instruction=SYSTEM_INSTRUCTION)


async def format_schedule(events: list[dict]) -> str:
    """
    Generate a readable schedule summary from a list of calendar events.

    Args:
        events: List of Google Calendar event dicts.

    Returns:
        Human-readable schedule summary.
    """
    if not events:
        return "You have no events scheduled for that time period."

    # Build a compact summary for the LLM
    event_lines: list[str] = []
    for e in events:
        summary = e.get("summary", "Untitled event")
        start = e.get("start", {})
        start_str = start.get("dateTime", start.get("date", "unknown time"))
        end = e.get("end", {})
        end_str = end.get("dateTime", end.get("date", ""))
        cal_name = e.get("_calendar_name", "")

        line = f"- {summary} | Start: {start_str}"
        if end_str:
            line += f" | End: {end_str}"
        if cal_name:
            line += f" | Calendar: {cal_name}"
        event_lines.append(line)

    events_text = "\n".join(event_lines)

    prompt = (
        f"Here are the user's upcoming events:\n{events_text}\n\n"
        "Summarize this schedule in a friendly, concise way. "
        "Group by day if spanning multiple days. Use natural time references "
        "like 'tomorrow' or 'Monday' when appropriate. "
        "Don't include calendar names unless the user has events on multiple calendars."
    )
    return await generate(prompt, system_instruction=SYSTEM_INSTRUCTION)


async def generate_clarification(question_type: str, context: dict) -> str:
    """
    Generate a natural follow-up question for the user.

    Args:
        question_type: One of "recurrence_scope", "event_selection", "end_time", "confirmation".
        context: Additional context for generating the question.

    Returns:
        A natural clarification question.
    """
    prompts = {
        "recurrence_scope": (
            f"The user wants to modify a recurring event: \"{context.get('title', 'an event')}\".\n"
            "Ask them whether they want to change just this occurrence or the entire series. "
            "Be brief and natural."
        ),
        "event_selection": (
            f"Multiple events matched the user's query. Here are the options:\n"
            + "\n".join(
                f"{i+1}. {e.get('summary', 'Untitled')} — {e.get('start', {}).get('dateTime', 'unknown time')}"
                for i, e in enumerate(context.get("events", []))
            )
            + "\nAsk the user which one they mean. List them with numbers. Be brief."
        ),
        "end_time": (
            f"The user wants to create an event: \"{context.get('title', 'an event')}\" "
            f"starting at {context.get('start', 'the specified time')}.\n"
            "They didn't specify an end time. Ask when they'd like it to end. Be brief."
        ),
        "confirmation": (
            f"Ask the user to confirm this action: {context.get('action', 'the requested change')}. "
            "Be brief and natural."
        ),
    }

    prompt = prompts.get(question_type, f"Ask a clarification question about: {context}")
    return await generate(prompt, system_instruction=SYSTEM_INSTRUCTION)
