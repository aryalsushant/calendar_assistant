"""
Calendar event operations — CRUD + recurrence-aware helpers.
"""

from datetime import datetime

from gcal.google_client import get_calendar_service, list_calendars


def get_events(
    calendar_id: str,
    time_min: datetime,
    time_max: datetime,
) -> list[dict]:
    """
    Fetch events from a single calendar within a time range.

    Args:
        calendar_id: Google Calendar ID (e.g. "primary").
        time_min: Start of range (timezone-aware).
        time_max: End of range (timezone-aware).

    Returns:
        List of event dicts from the Calendar API.
    """
    service = get_calendar_service()
    result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return result.get("items", [])


def get_events_all_calendars(
    time_min: datetime,
    time_max: datetime,
) -> list[dict]:
    """
    Fetch events across ALL calendars the user has access to.

    Returns a merged, chronologically sorted list of events.
    Each event dict is augmented with a '_calendar_id' key.
    """
    calendars = list_calendars()
    all_events: list[dict] = []

    for cal in calendars:
        cal_id = cal["id"]
        try:
            events = get_events(cal_id, time_min, time_max)
            for event in events:
                event["_calendar_id"] = cal_id
                event["_calendar_name"] = cal.get("summary", cal_id)
            all_events.extend(events)
        except Exception:
            # Skip calendars we can't read (e.g. holidays, birthdays)
            continue

    # Sort by start time
    def _start_key(e: dict) -> str:
        start = e.get("start", {})
        return start.get("dateTime", start.get("date", ""))

    all_events.sort(key=_start_key)
    return all_events


def create_event(
    calendar_id: str,
    summary: str,
    start: datetime,
    end: datetime,
    attendees: list[str] | None = None,
    description: str | None = None,
    timezone: str | None = None,
) -> dict:
    """
    Create a new calendar event.

    Args:
        calendar_id: Target calendar.
        summary: Event title.
        start: Start datetime (timezone-aware).
        end: End datetime (timezone-aware).
        attendees: Optional list of email addresses.
        description: Optional event description.
        timezone: Optional IANA timezone for the event.

    Returns:
        The created event dict from the API.
    """
    service = get_calendar_service()

    tz = timezone or start.tzinfo.key if hasattr(start.tzinfo, "key") else str(start.tzinfo)

    body: dict = {
        "summary": summary,
        "start": {"dateTime": start.isoformat(), "timeZone": tz},
        "end": {"dateTime": end.isoformat(), "timeZone": tz},
    }

    if description:
        body["description"] = description

    if attendees:
        body["attendees"] = [{"email": email} for email in attendees]

    return service.events().insert(calendarId=calendar_id, body=body).execute()


def delete_event(
    calendar_id: str,
    event_id: str,
    scope: str = "single",
) -> int:
    """
    Delete an event or an entire recurring series.

    Args:
        calendar_id: Calendar containing the event.
        event_id: The event ID to delete.
        scope: "single" to delete just this occurrence,
               "series" to delete the entire recurring series.

    Returns:
        Number of events affected.
    """
    service = get_calendar_service()

    if scope == "series":
        # Get the recurring event ID (the parent series)
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        series_id = event.get("recurringEventId", event_id)

        # Count future occurrences before deleting
        count = count_future_occurrences(calendar_id, series_id)

        # Delete the entire series by deleting the parent event
        service.events().delete(calendarId=calendar_id, eventId=series_id).execute()
        return max(count, 1)
    else:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        return 1


def update_event(
    calendar_id: str,
    event_id: str,
    updates: dict,
    scope: str = "single",
) -> tuple[dict, int]:
    """
    Update an event or an entire recurring series.

    Args:
        calendar_id: Calendar containing the event.
        event_id: The event ID to update.
        updates: Dict of fields to update (e.g. summary, start, end).
        scope: "single" or "series".

    Returns:
        Tuple of (updated event dict, number of events affected).
    """
    service = get_calendar_service()

    if scope == "series":
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        series_id = event.get("recurringEventId", event_id)
        count = count_future_occurrences(calendar_id, series_id)

        # Get the parent recurring event and patch it
        parent = service.events().get(calendarId=calendar_id, eventId=series_id).execute()
        parent.update(updates)
        updated = (
            service.events()
            .update(calendarId=calendar_id, eventId=series_id, body=parent)
            .execute()
        )
        return updated, max(count, 1)
    else:
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        event.update(updates)
        updated = (
            service.events()
            .update(calendarId=calendar_id, eventId=event_id, body=event)
            .execute()
        )
        return updated, 1


def is_recurring(event: dict) -> bool:
    """Check whether an event belongs to a recurring series."""
    return bool(event.get("recurringEventId"))


def count_future_occurrences(
    calendar_id: str,
    recurring_event_id: str,
) -> int:
    """
    Count the number of future occurrences of a recurring event series.

    Args:
        calendar_id: Calendar containing the series.
        recurring_event_id: The parent recurring event ID.

    Returns:
        Number of future instances.
    """
    from utils.datetime_utils import now_in_tz

    service = get_calendar_service()
    now = now_in_tz()

    instances = (
        service.events()
        .instances(
            calendarId=calendar_id,
            eventId=recurring_event_id,
            timeMin=now.isoformat(),
            maxResults=250,
        )
        .execute()
    )
    return len(instances.get("items", []))
