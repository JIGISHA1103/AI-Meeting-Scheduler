from google_auth_oauthlib.flow import Flow

from app.config import (
    CREDENTIALS_FILE,
    SCOPES,
    REDIRECT_URI,
)


def create_oauth_flow():
    """
    Creates and returns the Google OAuth flow.
    """
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES
    )

    flow.redirect_uri = REDIRECT_URI

    return flow