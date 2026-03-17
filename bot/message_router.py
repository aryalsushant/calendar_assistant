"""
Message router — core orchestration logic.

Takes an incoming user message, checks for pending conversation state,
parses intent, executes the appropriate calendar action, and returns a response.
"""

import logging

from bot.state_store import get_state, set_state, clear_state
from gcal.event_service import (
    get_events_all_calendars,
    create_event,
    delete_event,
    update_event,
    is_recurring,
)
from llm.intent_parser import parse_intent
from llm.response_generator import (
    generate_response,
    format_schedule,
    generate_clarification,
)
from utils.datetime_utils import (
    parse_datetime,
    get_time_range,
    format_datetime,
    now_in_tz,
)
from utils.fuzzy_match import find_matching_events
from config.settings import DEFAULT_TIMEZONE

logger = logging.getLogger(__name__)


async def handle_message(chat_id: int, text: str) -> str:
    """
    Process an incoming message and return a response string.

    Handles both fresh intents and follow-up answers to pending questions.
    """
    try:
        # Check for pending conversation state
        state = get_state(chat_id)
        if state:
            return await _handle_followup(chat_id, text, state)

        # Parse intent from scratch
        intent = await parse_intent(text)
        logger.info("Parsed intent: %s", intent)

        intent_type = intent.get("intent", "unknown")

        if intent_type == "get_schedule":
            return await _handle_get_schedule(chat_id, intent)
        elif intent_type == "create_event":
            return await _handle_create_event(chat_id, intent)
        elif intent_type == "delete_event":
            return await _handle_delete_event(chat_id, intent)
        elif intent_type == "update_event":
            return await _handle_update_event(chat_id, intent)
        elif intent_type == "error":
            return f"Sorry, I had trouble understanding that. {intent.get('reason', '')}"
        else:
            return (
                "I'm not sure what you'd like me to do. "
                "I can check your schedule, create events, update events, or cancel events. "
                "Could you rephrase that?"
            )

    except Exception as e:
        logger.exception("Error handling message")
        return f"Something went wrong: {e}. Please try again."


# ── Intent Handlers ──────────────────────────────────────────────────────────


async def _handle_get_schedule(chat_id: int, intent: dict) -> str:
    """Fetch and summarize the user's schedule."""
    tz = intent.get("timezone") or DEFAULT_TIMEZONE
    time_range_text = intent.get("time_range") or "today"

    time_range = get_time_range(time_range_text, tz)
    if not time_range:
        return "I couldn't understand that time range. Could you rephrase?"

    start, end = time_range
    events = get_events_all_calendars(start, end)
    return await format_schedule(events)


async def _handle_create_event(chat_id: int, intent: dict) -> str:
    """Create a new calendar event, asking for end time if missing."""
    tz = intent.get("timezone") or DEFAULT_TIMEZONE
    title = intent.get("title")
    dt_str = intent.get("datetime")
    end_dt_str = intent.get("end_datetime")

    if not title:
        return "What should I call this event?"

    if not dt_str:
        return "When should I schedule this event?"

    start = parse_datetime(dt_str, tz)
    if not start:
        return "I couldn't parse that date/time. Could you rephrase?"

    # If no end time → ask
    if not end_dt_str:
        set_state(chat_id, {
            "status": "awaiting_end_time",
            "intent": intent,
            "start_iso": start.isoformat(),
        })
        clarification = await generate_clarification("end_time", {
            "title": title,
            "start": format_datetime(start),
        })
        return clarification

    end = parse_datetime(end_dt_str, tz)
    if not end:
        return "I couldn't parse the end time. Could you try again?"

    return await _execute_create(chat_id, intent, start, end, tz)


async def _execute_create(
    chat_id: int,
    intent: dict,
    start,
    end,
    tz: str,
) -> str:
    """Actually create the event and return a confirmation."""
    title = intent.get("title", "Untitled Event")
    attendees = intent.get("attendees", [])

    event = create_event(
        calendar_id="primary",
        summary=title,
        start=start,
        end=end,
        attendees=attendees if attendees else None,
        timezone=tz,
    )

    clear_state(chat_id)

    result = {
        "action": "created",
        "summary": event.get("summary", title),
        "start": format_datetime(start),
        "end": format_datetime(end),
    }
    if attendees:
        result["attendees"] = attendees

    return await generate_response(result)


async def _handle_delete_event(chat_id: int, intent: dict) -> str:
    """Find and delete an event, handling ambiguity and recurrence."""
    return await _find_and_act(chat_id, intent, action="delete")


async def _handle_update_event(chat_id: int, intent: dict) -> str:
    """Find and update an event, handling ambiguity and recurrence."""
    return await _find_and_act(chat_id, intent, action="update")


async def _find_and_act(chat_id: int, intent: dict, action: str) -> str:
    """
    Shared logic for delete/update: find matching events, handle disambiguation,
    check recurrence scope, then execute.
    """
    tz = intent.get("timezone") or DEFAULT_TIMEZONE
    title = intent.get("title")
    dt_str = intent.get("datetime")

    if not title:
        return f"Which event would you like to {action}?"

    # Build a search window
    if dt_str:
        parsed = parse_datetime(dt_str, tz)
        if parsed:
            time_range = get_time_range(dt_str, tz)
        else:
            time_range = None
    else:
        time_range = None

    # Default: search next 7 days if no date given
    if not time_range:
        now = now_in_tz(tz)
        from datetime import timedelta
        time_range = (now, now + timedelta(days=7))

    start, end = time_range
    events = get_events_all_calendars(start, end)

    # Fuzzy match
    matches = find_matching_events(title, events)

    if not matches:
        return f"I couldn't find any event matching \"{title}\" in that time range."

    if len(matches) == 1:
        event, score = matches[0]
        return await _check_recurrence_and_act(chat_id, event, intent, action)

    # Multiple matches → ask user to pick
    top_matches = matches[:5]
    events_for_clarification = [e for e, _ in top_matches]

    set_state(chat_id, {
        "status": "awaiting_event_selection",
        "action": action,
        "intent": intent,
        "candidates": [
            {
                "id": e.get("id"),
                "summary": e.get("summary", "Untitled"),
                "start": e.get("start", {}).get("dateTime", e.get("start", {}).get("date", "")),
                "calendar_id": e.get("_calendar_id", "primary"),
            }
            for e in events_for_clarification
        ],
    })

    clarification = await generate_clarification("event_selection", {
        "events": events_for_clarification,
    })
    return clarification


async def _check_recurrence_and_act(
    chat_id: int,
    event: dict,
    intent: dict,
    action: str,
) -> str:
    """Check if event is recurring and scope is specified, then execute or ask."""
    scope = intent.get("recurrence_scope", "unspecified")

    if is_recurring(event) and scope == "unspecified":
        # Must ask before proceeding
        set_state(chat_id, {
            "status": "awaiting_recurrence_scope",
            "action": action,
            "intent": intent,
            "event_id": event["id"],
            "event_summary": event.get("summary", "Untitled"),
            "calendar_id": event.get("_calendar_id", "primary"),
        })
        clarification = await generate_clarification("recurrence_scope", {
            "title": event.get("summary", "this event"),
        })
        return clarification

    # Non-recurring or scope already specified
    effective_scope = "single" if not is_recurring(event) else scope
    return await _execute_action(chat_id, event, intent, action, effective_scope)


async def _execute_action(
    chat_id: int,
    event: dict,
    intent: dict,
    action: str,
    scope: str,
) -> str:
    """Execute the delete or update action and return confirmation."""
    calendar_id = event.get("_calendar_id", "primary")
    event_id = event["id"]

    if action == "delete":
        count = delete_event(calendar_id, event_id, scope=scope)
        clear_state(chat_id)

        result = {
            "action": "deleted",
            "summary": event.get("summary", "the event"),
            "count": count,
            "scope": scope,
        }
        if count > 1:
            result["detail"] = f"{count} upcoming events in the series"
        return await generate_response(result)

    elif action == "update":
        tz = intent.get("timezone") or DEFAULT_TIMEZONE
        update_fields = intent.get("update_fields", {})
        api_updates = {}

        # Handle datetime move
        new_dt_str = update_fields.get("new_datetime")
        if new_dt_str:
            new_dt = parse_datetime(new_dt_str, tz)
            if new_dt:
                api_updates["start"] = {
                    "dateTime": new_dt.isoformat(),
                    "timeZone": tz,
                }
                # Preserve original duration
                orig_start = event.get("start", {}).get("dateTime")
                orig_end = event.get("end", {}).get("dateTime")
                if orig_start and orig_end:
                    from datetime import datetime as dt_cls
                    try:
                        os = dt_cls.fromisoformat(orig_start)
                        oe = dt_cls.fromisoformat(orig_end)
                        duration = oe - os
                        new_end = new_dt + duration
                        api_updates["end"] = {
                            "dateTime": new_end.isoformat(),
                            "timeZone": tz,
                        }
                    except ValueError:
                        pass

        # Handle new end time
        new_end_str = update_fields.get("new_end_datetime")
        if new_end_str:
            new_end = parse_datetime(new_end_str, tz)
            if new_end:
                api_updates["end"] = {
                    "dateTime": new_end.isoformat(),
                    "timeZone": tz,
                }

        # Handle title rename
        new_title = update_fields.get("new_title")
        if new_title:
            api_updates["summary"] = new_title

        if not api_updates:
            clear_state(chat_id)
            return "I'm not sure what to update. Could you clarify the changes?"

        updated, count = update_event(calendar_id, event_id, api_updates, scope=scope)
        clear_state(chat_id)

        result = {
            "action": "updated",
            "summary": updated.get("summary", event.get("summary", "the event")),
            "count": count,
            "scope": scope,
            "changes": list(api_updates.keys()),
        }
        return await generate_response(result)

    clear_state(chat_id)
    return "Something unexpected happened. Please try again."


# ── Follow-up Handler ────────────────────────────────────────────────────────


async def _handle_followup(chat_id: int, text: str, state: dict) -> str:
    """Handle a follow-up answer to a pending question."""
    status = state.get("status")

    if status == "awaiting_end_time":
        return await _followup_end_time(chat_id, text, state)
    elif status == "awaiting_event_selection":
        return await _followup_event_selection(chat_id, text, state)
    elif status == "awaiting_recurrence_scope":
        return await _followup_recurrence_scope(chat_id, text, state)
    else:
        # Unknown state — reset and process as new message
        clear_state(chat_id)
        return await handle_message(chat_id, text)


async def _followup_end_time(chat_id: int, text: str, state: dict) -> str:
    """User provided an end time for event creation."""
    intent = state.get("intent", {})
    tz = intent.get("timezone") or DEFAULT_TIMEZONE
    start_iso = state.get("start_iso")

    from datetime import datetime as dt_cls
    start = dt_cls.fromisoformat(start_iso)

    end = parse_datetime(text, tz)
    if not end:
        return "I couldn't parse that end time. Could you try again? (e.g. '2pm' or '1 hour')"

    # Handle duration-like inputs (e.g., "1 hour")
    # If the parsed end is before start, it might be a duration
    if end <= start:
        # Try interpreting as duration from start
        import re
        match = re.search(r"(\d+)\s*(hour|hr|minute|min)", text.lower())
        if match:
            from datetime import timedelta
            amount = int(match.group(1))
            unit = match.group(2)
            if unit.startswith("hour") or unit.startswith("hr"):
                end = start + timedelta(hours=amount)
            else:
                end = start + timedelta(minutes=amount)
        else:
            return "The end time seems to be before the start time. Could you double-check?"

    return await _execute_create(chat_id, intent, start, end, tz)


async def _followup_event_selection(chat_id: int, text: str, state: dict) -> str:
    """User selected an event from a numbered list."""
    candidates = state.get("candidates", [])
    action = state.get("action", "delete")
    intent = state.get("intent", {})

    # Try to extract a number
    import re
    match = re.search(r"\d+", text)
    if not match:
        return "Please reply with the number of the event you mean."

    idx = int(match.group()) - 1  # 1-indexed → 0-indexed
    if idx < 0 or idx >= len(candidates):
        return f"Please pick a number between 1 and {len(candidates)}."

    selected = candidates[idx]
    event_id = selected["id"]
    calendar_id = selected.get("calendar_id", "primary")

    # Fetch the full event
    from gcal.google_client import get_calendar_service
    service = get_calendar_service()
    event = service.events().get(
        calendarId=calendar_id, eventId=event_id,
    ).execute()
    event["_calendar_id"] = calendar_id

    clear_state(chat_id)
    return await _check_recurrence_and_act(chat_id, event, intent, action)


async def _followup_recurrence_scope(chat_id: int, text: str, state: dict) -> str:
    """User answered whether to affect single occurrence or entire series."""
    lower = text.lower().strip()
    action = state.get("action", "delete")
    intent = state.get("intent", {})
    event_id = state.get("event_id")
    calendar_id = state.get("calendar_id", "primary")

    # Determine scope from user's reply
    series_keywords = ["series", "all", "every", "entire", "whole"]
    single_keywords = ["this", "just", "single", "one", "only"]

    scope = "unspecified"
    if any(kw in lower for kw in series_keywords):
        scope = "series"
    elif any(kw in lower for kw in single_keywords):
        scope = "single"

    if scope == "unspecified":
        return "I need to know — should I change just this one occurrence, or the entire series?"

    # Fetch the event
    from gcal.google_client import get_calendar_service
    service = get_calendar_service()
    event = service.events().get(
        calendarId=calendar_id, eventId=event_id,
    ).execute()
    event["_calendar_id"] = calendar_id

    clear_state(chat_id)
    return await _execute_action(chat_id, event, intent, action, scope)
