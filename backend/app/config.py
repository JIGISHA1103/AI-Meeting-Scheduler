import os

# BACKEND directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Google OAuth files
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")

# OAuth Redirect URI
REDIRECT_URI = "http://localhost:8000/auth/callback"

# Google Calendar Scope
SCOPES = [
    "https://www.googleapis.com/auth/calendar"
]