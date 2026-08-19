import os
import json
import traceback
import uuid
from datetime import datetime

# --------------------------------------------------
# Allow HTTP for local development only
# --------------------------------------------------

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# --------------------------------------------------
# FastAPI imports
# --------------------------------------------------

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

# --------------------------------------------------
# Application imports
# --------------------------------------------------

from app.ai.parser import parse_meeting_request
from app.auth.oauth import create_oauth_flow

# Celery task
from app.tasks import process_meeting_request

from app.calendar.calendar_service import (
    get_calendar_service,
    check_availability,
    create_calendar_event
)

# --------------------------------------------------
# Database imports
# --------------------------------------------------

from app.database.database import SessionLocal
from app.database.models import MeetingRequest as MeetingRequestDB


# ==================================================
# FastAPI Application
# ==================================================

app = FastAPI(
    title="Meeting AI",
    version="1.0"
)


# ==================================================
# Request Models
# ==================================================

class MeetingRequest(BaseModel):
    text: str


class CalendarEventRequest(BaseModel):
    summary: str
    start: str
    end: str
    description: str = ""


# ==================================================
# Temporary OAuth Flow Storage
# ==================================================

oauth_flows = {}


# ==================================================
# OAuth Token Storage
# ==================================================

TOKEN_FILE = "token.json"


def save_credentials(credentials):
    """
    Save Google OAuth credentials locally.
    """

    token_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes
    }

    with open(TOKEN_FILE, "w") as token_file:
        json.dump(
            token_data,
            token_file,
            indent=4
        )


# ==================================================
# Home
# ==================================================

@app.get("/")
def home():

    return {
        "status": "success",
        "message": "Meeting AI Backend is running!"
    }


# ==================================================
# Google OAuth Login
# ==================================================

@app.get("/login")
def login():

    try:

        flow = create_oauth_flow()

        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent"
        )

        # Store the original OAuth flow.
        # This preserves the PKCE code verifier.
        oauth_flows[state] = flow

        return RedirectResponse(
            url=authorization_url
        )

    except Exception as e:

        traceback.print_exc()

        return {
            "error": str(e)
        }


# ==================================================
# Google OAuth Callback
# ==================================================

@app.get("/auth/callback")
def auth_callback(request: Request):

    try:

        # --------------------------------------------------
        # Get OAuth state
        # --------------------------------------------------

        state = request.query_params.get("state")

        if not state:

            return {
                "error": "Missing OAuth state"
            }

        # --------------------------------------------------
        # Retrieve original OAuth flow
        # --------------------------------------------------

        flow = oauth_flows.get(state)

        if not flow:

            return {
                "error": (
                    "OAuth flow not found or expired. "
                    "Please login again."
                )
            }

        # --------------------------------------------------
        # Exchange authorization code
        # for Google credentials
        # --------------------------------------------------

        flow.fetch_token(
            authorization_response=str(request.url)
        )

        credentials = flow.credentials

        # --------------------------------------------------
        # Save credentials locally
        # --------------------------------------------------

        save_credentials(credentials)

        # --------------------------------------------------
        # Remove OAuth flow after successful authentication
        # --------------------------------------------------

        oauth_flows.pop(state, None)

        # DO NOT return the tokens
        return {
            "message": "Google Calendar connected successfully"
        }

    except Exception as e:

        traceback.print_exc()

        return {
            "error": str(e)
        }


# ==================================================
# Existing Parse Endpoint
# ==================================================

@app.post("/parse")
def parse(request: MeetingRequest):

    try:

        return parse_meeting_request(
            request.text
        )

    except Exception as e:

        traceback.print_exc()

        return {
            "error": str(e)
        }


# ==================================================
# Google Calendar Test
# ==================================================

@app.get("/calendar")
def get_calendar():

    try:

        service = get_calendar_service()

        calendar = service.calendars().get(
            calendarId="primary"
        ).execute()

        return {
            "message": (
                "Google Calendar API connected successfully"
            ),
            "calendar_id": calendar.get("id"),
            "calendar_name": calendar.get("summary"),
            "timezone": calendar.get("timeZone")
        }

    except Exception as e:

        traceback.print_exc()

        return {
            "error": str(e)
        }


# ==================================================
# Google Calendar Availability
# ==================================================

@app.get("/calendar/availability")
def calendar_availability():

    try:

        start_time = datetime.fromisoformat(
            "2026-08-10T15:00:00+05:30"
        )

        end_time = datetime.fromisoformat(
            "2026-08-10T15:30:00+05:30"
        )

        busy_periods = check_availability(
            start_time,
            end_time
        )

        return {
            "requested_start": start_time.isoformat(),
            "requested_end": end_time.isoformat(),
            "busy_periods": busy_periods,
            "available": len(busy_periods) == 0
        }

    except Exception as e:

        traceback.print_exc()

        return {
            "error": str(e)
        }


# ==================================================
# Create Google Calendar Event
# ==================================================

@app.post("/calendar/create-event")
def create_event(request: CalendarEventRequest):

    try:

        start_time = datetime.fromisoformat(
            request.start
        )

        end_time = datetime.fromisoformat(
            request.end
        )

        created_event = create_calendar_event(
            summary=request.summary,
            start_time=start_time,
            end_time=end_time,
            description=request.description
        )

        return {
            "message": (
                "Google Calendar event created successfully"
            ),
            "event": created_event
        }

    except Exception as e:

        traceback.print_exc()

        return {
            "error": str(e)
        }


# ==================================================
# PHASE 14
# ASYNCHRONOUS TASK PROCESSING
# ==================================================

@app.post("/schedule")
def schedule(request: MeetingRequest):

    # --------------------------------------------------
    # Generate unique request ID
    # --------------------------------------------------

    request_id = str(uuid.uuid4())

    print(
        f"[{request_id}] Request received"
    )

    # --------------------------------------------------
    # Open database session
    # --------------------------------------------------

    db = SessionLocal()

    db_request = None

    try:

        # --------------------------------------------------
        # Save request to database
        # --------------------------------------------------

        db_request = MeetingRequestDB(
            request_id=request_id,
            user_input=request.text,
            status="processing"
        )

        db.add(db_request)

        db.commit()

        db.refresh(db_request)

        print(
            f"[{request_id}] Request saved to database"
        )

        # --------------------------------------------------
        # Send request to Celery
        # --------------------------------------------------

        task = process_meeting_request.delay(
            request.text,
            request_id
        )

        print(
            f"[{request_id}] Celery task queued: "
            f"{task.id}"
        )

        # --------------------------------------------------
        # Return immediately
        # --------------------------------------------------

        return {
            "request_id": request_id,
            "task_id": task.id,
            "status": "processing",
            "message": "Meeting request queued successfully"
        }

    except Exception as e:

        # --------------------------------------------------
        # Celery queueing failure
        # --------------------------------------------------

        print(
            f"[{request_id}] Failed to queue Celery task"
        )

        traceback.print_exc()

        error_message = str(e)

        # --------------------------------------------------
        # Update database with error
        # --------------------------------------------------

        if db_request:

            db_request.status = "error"

            db_request.error_message = error_message

            db_request.completed_at = datetime.utcnow()

            db.commit()

        return {
            "request_id": request_id,
            "status": "error",
            "message": error_message
        }

    finally:

        # --------------------------------------------------
        # Always close database session
        # --------------------------------------------------

        db.close()