"""
Fuzzy matching utilities for finding calendar events by title/description.
"""

from thefuzz import fuzz


def find_matching_events(
    query: str,
    events: list[dict],
    threshold: int = 55,
) -> list[tuple[dict, int]]:
    """
    Rank calendar events by fuzzy similarity to the query string.

    Matches against event summary (title), description, and attendee names.

    Args:
        query: The search phrase (e.g. "meeting with Bipul").
        events: List of Google Calendar event dicts.
        threshold: Minimum score (0-100) to include in results.

    Returns:
        List of (event, score) tuples sorted by score descending.
    """
    scored: list[tuple[dict, int]] = []

    query_lower = query.lower().strip()

    for event in events:
        best_score = 0

        # Match against title
        summary = event.get("summary", "")
        if summary:
            title_score = fuzz.token_set_ratio(query_lower, summary.lower())
            best_score = max(best_score, title_score)

        # Match against description
        description = event.get("description", "")
        if description:
            desc_score = fuzz.token_set_ratio(query_lower, description.lower())
            best_score = max(best_score, desc_score)

        # Match against attendee display names and emails
        attendees = event.get("attendees", [])
        for attendee in attendees:
            name = attendee.get("displayName", "")
            email = attendee.get("email", "")
            if name:
                att_score = fuzz.token_set_ratio(query_lower, name.lower())
                best_score = max(best_score, att_score)
            if email:
                email_name = email.split("@")[0].replace(".", " ")
                email_score = fuzz.token_set_ratio(query_lower, email_name.lower())
                best_score = max(best_score, email_score)

        if best_score >= threshold:
            scored.append((event, best_score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored
