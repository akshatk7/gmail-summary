#!/usr/bin/env python3
"""Builds an authenticated Gmail API service."""

from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# 1. We only need 'read/modify' + 'send' later.
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

def get_service():
    """
    Returns a Gmail API service object.
    * On first run, opens a browser to ask permission.
    * Caches the resulting token in token.json for reuse.
    """
    creds = None
    token_path = Path("token.json")

    if token_path.exists():
        # 2. Reuse saved credentials
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        # 3. Refresh or start OAuth browser flow
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)  # Opens default browser
        # 4. Save the token for next time
        token_path.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)
