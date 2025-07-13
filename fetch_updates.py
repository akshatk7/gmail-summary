#!/usr/bin/env python3
"""
Count messages in Updates & Promotions from the past 7 days.
"""

from datetime import datetime, timedelta
from gmail_service import get_service

def main():
    service = get_service()
    cutoff = (datetime.utcnow() - timedelta(days=7)).strftime("%Y/%m/%d")
    query = f"after:{cutoff} (label:updates OR label:promotions)"
    print("Gmail search query:", query)

    resp = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=500)
        .execute()
    )

    messages = resp.get("messages", [])
    print(f"→ Found {len(messages)} message(s) in the last week.")

if __name__ == "__main__":
    main()
