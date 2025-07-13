#!/usr/bin/env python3
"""
Count messages in Updates & Promotions from the past 7 days.
"""

from datetime import datetime, timedelta
from gmail_service import get_service

def fetch_and_print(service, label, label_name):
    cutoff = (datetime.utcnow() - timedelta(days=7)).strftime("%Y/%m/%d")
    query = f"after:{cutoff} label:{label}"
    print(f"\n--- {label_name} ---")
    resp = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=5)
        .execute()
    )
    messages = resp.get("messages", [])
    print(f"Found {len(messages)} message(s) in {label_name} in the last week.")
    for msg in messages:
        msg_detail = service.users().messages().get(userId="me", id=msg["id"], format="metadata", metadataHeaders=["Subject", "From"]).execute()
        headers = {h["name"]: h["value"] for h in msg_detail["payload"]["headers"]}
        subject = headers.get("Subject", "(No Subject)")
        sender = headers.get("From", "(No Sender)")
        print(f"Subject: {subject}")
        print(f"From: {sender}\n")


def main():
    service = get_service()
    fetch_and_print(service, "promotions", "Promotions")
    fetch_and_print(service, "updates", "Updates")

if __name__ == "__main__":
    main()
