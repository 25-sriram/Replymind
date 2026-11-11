
import os
import secrets

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose"
]

REDIRECT_URI = "http://localhost:5000/oauth2callback"


def get_authorization_url():
    code_verifier = secrets.token_urlsafe(64)

    flow = Flow.from_client_secrets_file(
        "credentials.json",
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
        code_verifier=code_verifier
    )

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )

    return authorization_url, state, code_verifier


def get_credentials_from_code(code, code_verifier):
    flow = Flow.from_client_secrets_file(
        "credentials.json",
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
        code_verifier=code_verifier
    )

    flow.fetch_token(code=code)

    return flow.credentials


def save_credentials(credentials):
    with open("token.json", "w") as token:
        token.write(credentials.to_json())


def get_gmail_service():
    credentials = None

    if os.path.exists("token.json"):
        credentials = Credentials.from_authorized_user_file(
            "token.json", SCOPES
        )

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        save_credentials(credentials)

    if not credentials or not credentials.valid:
        return None

    return build("gmail", "v1", credentials=credentials)
