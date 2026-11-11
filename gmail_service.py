
import base64
from email.message import EmailMessage
from email.utils import parseaddr

from gmail_auth import get_gmail_service


def decode_email_data(data):
    """Decode Gmail's URL-safe Base64 email content."""
    if not data:
        return ""

    padding = "=" * (-len(data) % 4)

    decoded = base64.urlsafe_b64decode(data + padding)

    return decoded.decode("utf-8", errors="replace")


def get_email_body(payload):
    """Extract the plain-text body from an email."""

    body = ""

    mime_type = payload.get("mimeType", "")

    if mime_type == "text/plain":
        data = payload.get("body", {}).get("data")
        return decode_email_data(data)

    parts = payload.get("parts", [])

    for part in parts:
        body += get_email_body(part)

    return body


def get_email_headers(payload):
    """Return the email headers."""

    headers = payload.get("headers", [])

    def get_header(name):
        return next(
            (
                header["value"]
                for header in headers
                if header["name"].lower() == name.lower()
            ),
            ""
        )

    return get_header


def fetch_emails(max_results=10):
    """Fetch recent emails from the Gmail inbox."""

    service = get_gmail_service()

    if not service:
        return []

    results = service.users().messages().list(
        userId="me",
        maxResults=max_results,
        q="in:inbox"
    ).execute()

    messages = results.get("messages", [])

    emails = []

    for message in messages:

        msg = service.users().messages().get(
            userId="me",
            id=message["id"],
            format="full"
        ).execute()

        payload = msg.get("payload", {})
        get_header = get_email_headers(payload)

        emails.append({
            "id": msg["id"],
            "sender": get_header("From") or "Unknown",
            "subject": get_header("Subject") or "(No Subject)",
            "body": get_email_body(payload)
        })

    return emails


def get_email_by_id(email_id):
    """Fetch one complete email using its Gmail message ID."""

    service = get_gmail_service()

    if not service:
        raise Exception("Gmail is not connected.")

    msg = service.users().messages().get(
        userId="me",
        id=email_id,
        format="full"
    ).execute()

    payload = msg.get("payload", {})
    get_header = get_email_headers(payload)

    sender = get_header("From")

    return {
        "id": msg["id"],
        "thread_id": msg.get("threadId"),
        "sender": sender or "Unknown",
        "sender_email": parseaddr(sender)[1],
        "subject": get_header("Subject") or "(No Subject)",
        "message_id": get_header("Message-ID"),
        "references": get_header("References"),
        "body": get_email_body(payload)
    }


def create_gmail_draft(email_data, reply_text):
    """Create a reply draft in Gmail without sending it."""

    service = get_gmail_service()

    if not service:
        raise Exception("Gmail is not connected.")

    recipient = email_data.get("sender_email")

    if not recipient:
        raise ValueError(
            "Could not identify the sender's email address."
        )

    message = EmailMessage()

    message["To"] = recipient

    subject = email_data.get("subject", "(No Subject)")

    if subject.lower().startswith("re:"):
        message["Subject"] = subject
    else:
        message["Subject"] = "Re: " + subject

    if email_data.get("message_id"):
        message["In-Reply-To"] = email_data["message_id"]

    if email_data.get("references"):
        message["References"] = email_data["references"]
    elif email_data.get("message_id"):
        message["References"] = email_data["message_id"]

    message.set_content(reply_text)

    encoded_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode("utf-8")

    draft_body = {
        "message": {
            "raw": encoded_message,
            "threadId": email_data["thread_id"]
        }
    }

    draft = service.users().drafts().create(
        userId="me",
        body=draft_body
    ).execute()

    return draft
