"""
Google Calendar API client — handles OAuth2 authentication and service creation.
"""

import os
import json
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config.settings import (
    GOOGLE_CREDENTIALS_PATH,
    GOOGLE_TOKEN_PATH,
    GOOGLE_SCOPES,
    GOOGLE_OAUTH_CREDENTIALS_JSON,
    GOOGLE_OAUTH_TOKEN_JSON,
)

logger = logging.getLogger(__name__)


def get_calendar_service():
    """
    Build and return an authenticated Google Calendar API service.

    On first run, opens a browser for OAuth2 consent and saves the refresh
    token to token.json. Subsequent runs use the stored token silently.
    If running in the cloud (Railway), it loads tokens directly from env vars.
    """
    creds: Credentials | None = None

    # Priority 1: Load from Environment Variable (for Railway / Cloud deployments)
    if GOOGLE_OAUTH_TOKEN_JSON:
        try:
            token_info = json.loads(GOOGLE_OAUTH_TOKEN_JSON)
            creds = Credentials.from_authorized_user_info(token_info, GOOGLE_SCOPES)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse GOOGLE_OAUTH_TOKEN_JSON env var: %s", e)
            raise ValueError(f"Invalid JSON in GOOGLE_OAUTH_TOKEN_JSON: {e}")

    # Priority 2: Load existing token from file (local dev)
    elif os.path.exists(GOOGLE_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_PATH, GOOGLE_SCOPES)

    # Refresh or run full OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # We need to run the OAuth flow
            if GOOGLE_OAUTH_CREDENTIALS_JSON:
                try:
                    client_config = json.loads(GOOGLE_OAUTH_CREDENTIALS_JSON)
                    flow = InstalledAppFlow.from_client_config(client_config, GOOGLE_SCOPES)
                except json.JSONDecodeError as e:
                    logger.error("Failed to parse GOOGLE_OAUTH_CREDENTIALS_JSON: %s", e)
                    raise ValueError(f"Invalid JSON in GOOGLE_OAUTH_CREDENTIALS_JSON: {e}")
            elif os.path.exists(GOOGLE_CREDENTIALS_PATH):
                flow = InstalledAppFlow.from_client_secrets_file(
                    GOOGLE_CREDENTIALS_PATH, GOOGLE_SCOPES,
                )
            else:
                raise FileNotFoundError(
                    "OAuth2 credentials not found. Set GOOGLE_OAUTH_CREDENTIALS_JSON env var "
                    f"or download credentials.json to {GOOGLE_CREDENTIALS_PATH}."
                )
            creds = flow.run_local_server(port=0)

        # Save the token to local filesystem for the next run (if possible)
        try:
            with open(GOOGLE_TOKEN_PATH, "w") as token_file:
                token_file.write(creds.to_json())
        except OSError as e:
            logger.warning("Could not write token.json to disk: %s", e)

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
