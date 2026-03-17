"""
Google Calendar API client — handles OAuth2 authentication and service creation.
"""

import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource

from config.settings import GOOGLE_CREDENTIALS_PATH, GOOGLE_TOKEN_PATH, GOOGLE_SCOPES


def get_calendar_service() -> Resource:
    """
    Build and return an authenticated Google Calendar API service.

    On first run, opens a browser for OAuth2 consent and saves the refresh
    token to token.json. Subsequent runs use the stored token silently.
    """
    creds: Credentials | None = None

    # Load existing token
    if os.path.exists(GOOGLE_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_PATH, GOOGLE_SCOPES)

    # Refresh or run full OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(GOOGLE_CREDENTIALS_PATH):
                raise FileNotFoundError(
                    f"OAuth2 credentials file not found at {GOOGLE_CREDENTIALS_PATH}. "
                    "Download it from Google Cloud Console → APIs & Services → Credentials."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                GOOGLE_CREDENTIALS_PATH, GOOGLE_SCOPES,
            )
            creds = flow.run_local_server(port=0)

        # Save for next run
        with open(GOOGLE_TOKEN_PATH, "w") as token_file:
            token_file.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def list_calendars() -> list[dict]:
    """
    Return all calendars the authenticated user has access to.

    Returns:
        List of dicts with keys like 'id', 'summary', 'primary', etc.
    """
    service = get_calendar_service()
    result = service.calendarList().list().execute()
    return result.get("items", [])
