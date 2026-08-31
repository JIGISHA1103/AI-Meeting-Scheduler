import os
import json
import traceback
import uuid

from datetime import datetime

# ==================================================
# Allow HTTP for local development only
# ==================================================

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


# ==================================================
# FastAPI imports
# ==================================================

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel


# ==================================================
# Application imports
# ==================================================

from app.ai.parser import parse_meeting_request

from app.auth.oauth import create_oauth_flow

from app.calendar.calendar_service import (
    get_calendar_service,
    check_availability,
    create_calendar_event
)

from app.tasks import process_meeting_request


# ==================================================
# Database imports
# ==================================================

from app.database.database import SessionLocal

from app.database.models import MeetingRequest as MeetingRequestDB


# ==================================================
# Celery imports
# ==================================================

from celery.result import AsyncResult

from celery_app import celery_app


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

        "token":
            credentials.token,

        "refresh_token":
            credentials.refresh_token,

        "token_uri":
            credentials.token_uri,

        "client_id":
            credentials.client_id,

        "client_secret":
            credentials.client_secret,

        "scopes":
            credentials.scopes
    }

    with open(
        TOKEN_FILE,
        "w"
    ) as token_file:

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

        "message":
            "Meeting AI Backend is running!"
    }


# ==================================================
# Google OAuth Login
# ==================================================

@app.get("/login")
def login():

    try:

        flow = create_oauth_flow()

        authorization_url, state = (
            flow.authorization_url(

                access_type="offline",

                include_granted_scopes="true",

                prompt="consent"
            )
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

            "status": "error",

            "message": str(e)
        }


# ==================================================
# Google OAuth Callback
# ==================================================

@app.get("/auth/callback")
def auth_callback(
    request: Request
):

    try:

        # --------------------------------------------------
        # Get OAuth state
        # --------------------------------------------------

        state = request.query_params.get(
            "state"
        )

        if not state:

            return {

                "status": "error",

                "message":
                    "Missing OAuth state"
            }


        # --------------------------------------------------
        # Retrieve original OAuth flow
        # --------------------------------------------------

        flow = oauth_flows.get(
            state
        )

        if not flow:

            return {

                "status": "error",

                "message":
                    (
                        "OAuth flow not found or expired. "
                        "Please login again."
                    )
            }


        # --------------------------------------------------
        # Exchange authorization code
        # --------------------------------------------------

        flow.fetch_token(
            authorization_response=
                str(request.url)
        )

        credentials = flow.credentials


        # --------------------------------------------------
        # Save credentials locally
        # --------------------------------------------------

        save_credentials(
            credentials
        )


        # --------------------------------------------------
        # Remove OAuth flow
        # --------------------------------------------------

        oauth_flows.pop(
            state,
            None
        )


        # --------------------------------------------------
        # Do not return OAuth tokens
        # --------------------------------------------------

        return {

            "status": "success",

            "message":
                "Google Calendar connected successfully"
        }

    except Exception as e:

        traceback.print_exc()

        return {

            "status": "error",

            "message": str(e)
        }


# ==================================================
# Existing Parse Endpoint
# ==================================================

@app.post("/parse")
def parse(
    request: MeetingRequest
):

    try:

        return parse_meeting_request(
            request.text
        )

    except Exception as e:

        traceback.print_exc()

        return {

            "status": "error",

            "message": str(e)
        }


# ==================================================
# Google Calendar Test
# ==================================================

@app.get("/calendar")
def get_calendar():

    try:

        service = get_calendar_service()

        calendar = (
            service.calendars()
            .get(
                calendarId="primary"
            )
            .execute()
        )

        return {

            "status": "success",

            "message":
                (
                    "Google Calendar API "
                    "connected successfully"
                ),

            "calendar_id":
                calendar.get("id"),

            "calendar_name":
                calendar.get("summary"),

            "timezone":
                calendar.get("timeZone")
        }

    except Exception as e:

        traceback.print_exc()

        return {

            "status": "error",

            "message": str(e)
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

            "status": "success",

            "requested_start":
                start_time.isoformat(),

            "requested_end":
                end_time.isoformat(),

            "busy_periods":
                busy_periods,

            "available":
                len(busy_periods) == 0
        }

    except Exception as e:

        traceback.print_exc()

        return {

            "status": "error",

            "message": str(e)
        }


# ==================================================
# Create Google Calendar Event
# ==================================================

@app.post("/calendar/create-event")
def create_event(
    request: CalendarEventRequest
):

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

            "status": "success",

            "message":
                (
                    "Google Calendar event "
                    "created successfully"
                ),

            "event":
                created_event
        }

    except Exception as e:

        traceback.print_exc()

        return {

            "status": "error",

            "message": str(e)
        }


# ==================================================
# PHASE 14
# ASYNCHRONOUS TASK PROCESSING
# ==================================================

@app.post("/schedule")
def schedule(
    request: MeetingRequest
):

    # --------------------------------------------------
    # Generate unique request ID
    # --------------------------------------------------

    request_id = str(
        uuid.uuid4()
    )

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
        # Save request to PostgreSQL
        # --------------------------------------------------

        db_request = MeetingRequestDB(

            request_id=request_id,

            user_input=request.text,

            status="processing"
        )

        db.add(
            db_request
        )

        db.commit()

        db.refresh(
            db_request
        )

        print(
            f"[{request_id}] "
            f"Request saved to database"
        )


        # --------------------------------------------------
        # Send request to Celery
        # --------------------------------------------------

        task = process_meeting_request.delay(

            request.text,

            request_id
        )

        print(

            f"[{request_id}] "
            f"Celery task queued: "
            f"{task.id}"
        )


        # --------------------------------------------------
        # Save Celery task ID
        # --------------------------------------------------

        db_request.task_id = task.id

        db.commit()

        print(

            f"[{request_id}] "
            f"Celery task ID saved: "
            f"{task.id}"
        )


        # --------------------------------------------------
        # Return immediately
        # --------------------------------------------------

        return {

            "request_id":
                request_id,

            "task_id":
                task.id,

            "status":
                "processing",

            "message":
                "Meeting request queued successfully"
        }


    except Exception as e:

        # --------------------------------------------------
        # Celery queueing / database failure
        # --------------------------------------------------

        print(

            f"[{request_id}] "
            f"Failed to queue request"
        )

        traceback.print_exc()

        error_message = str(e)


        # --------------------------------------------------
        # Update database with error
        # --------------------------------------------------

        if db_request:

            try:

                db_request.status = "error"

                db_request.error_message = (
                    error_message
                )

                db_request.completed_at = (
                    datetime.utcnow()
                )

                db.commit()

            except Exception:

                db.rollback()

                traceback.print_exc()


        return {

            "request_id":
                request_id,

            "status":
                "error",

            "message":
                error_message
        }


    finally:

        # --------------------------------------------------
        # Always close database session
        # --------------------------------------------------

        db.close()


# ==================================================
# Check Meeting Request Status
# ==================================================

@app.get(
    "/schedule/status/{request_id}"
)
def get_schedule_status(
    request_id: str
):

    print(
        f"[{request_id}] "
        f"Status check received"
    )


    # --------------------------------------------------
    # Open database session
    # --------------------------------------------------

    db = SessionLocal()

    try:

        # --------------------------------------------------
        # Find request
        # --------------------------------------------------

        db_request = (

            db.query(
                MeetingRequestDB
            )

            .filter(

                MeetingRequestDB.request_id
                == request_id
            )

            .first()
        )


        # --------------------------------------------------
        # Request does not exist
        # --------------------------------------------------

        if not db_request:

            print(

                f"[{request_id}] "
                f"Request not found"
            )

            return {

                "request_id":
                    request_id,

                "status":
                    "not_found",

                "message":
                    "Request ID not found"
            }


        # --------------------------------------------------
        # Log current status
        # --------------------------------------------------

        print(

            f"[{request_id}] "
            f"Current status: "
            f"{db_request.status}"
        )


        # --------------------------------------------------
        # Still processing
        # --------------------------------------------------

        if db_request.status == "processing":

            return {

                "request_id":
                    db_request.request_id,

                "status":
                    "processing",

                "message":
                    "Meeting request is being processed."
            }


        # --------------------------------------------------
        # Failed request
        # --------------------------------------------------

        if db_request.status == "error":

            return {

                "request_id":
                    db_request.request_id,

                "status":
                    "error",

                "message":
                    (
                        db_request.error_message
                        or
                        "Meeting scheduling failed."
                    ),

                "error_message":
                    db_request.error_message
            }


        # --------------------------------------------------
        # Scheduling conflict
        # --------------------------------------------------

        if db_request.status == "conflict":

            return {

                "request_id":
                    db_request.request_id,

                "status":
                    "conflict",

                "message":
                    (
                        "The requested meeting "
                        "time is occupied."
                    )
            }


        # --------------------------------------------------
        # Successful request
        # --------------------------------------------------

        if db_request.status == "success":

            # --------------------------------------------------
            # Make sure task ID exists
            # --------------------------------------------------

            if not db_request.task_id:

                print(

                    f"[{request_id}] "
                    f"Task ID missing"
                )

                return {

                    "request_id":
                        db_request.request_id,

                    "status":
                        "error",

                    "message":
                        (
                            "Meeting was scheduled, "
                            "but the Celery task ID "
                            "is missing."
                        )
                }


            # --------------------------------------------------
            # Get Celery task result
            # --------------------------------------------------

            print(

                f"[{request_id}] "
                f"Fetching Celery result: "
                f"{db_request.task_id}"
            )

            task_result = AsyncResult(

                db_request.task_id,

                app=celery_app
            )


            print(

                f"[{request_id}] "
                f"Celery result state: "
                f"{task_result.state}"
            )


            # --------------------------------------------------
            # Make sure Celery task completed
            # --------------------------------------------------

            if not task_result.successful():

                print(

                    f"[{request_id}] "
                    f"Celery result not available yet"
                )

                return {

                    "request_id":
                        db_request.request_id,

                    "status":
                        "processing",

                    "message":
                        (
                            "Meeting is still "
                            "being finalized."
                        )
                }


            # --------------------------------------------------
            # Get complete scheduling result
            # --------------------------------------------------

            result = task_result.result


            if not isinstance(
                result,
                dict
            ):

                return {

                    "request_id":
                        db_request.request_id,

                    "status":
                        "success",

                    "message":
                        "Meeting scheduled successfully."
                }


            # --------------------------------------------------
            # Return complete result
            # --------------------------------------------------

            return {

                "request_id":
                    db_request.request_id,

                "status":
                    "success",

                "message":
                    result.get(
                        "message",
                        "Meeting scheduled successfully."
                    ),

                "meeting":
                    result.get(
                        "meeting"
                    ),

                "event":
                    result.get(
                        "event"
                    )
            }


        # --------------------------------------------------
        # Unknown status
        # --------------------------------------------------

        return {

            "request_id":
                db_request.request_id,

            "status":
                db_request.status,

            "message":
                (
                    f"Current request status: "
                    f"{db_request.status}"
                )
        }


    except Exception as e:

        traceback.print_exc()

        return {

            "request_id":
                request_id,

            "status":
                "error",

            "message":
                str(e)
        }


    finally:

        # --------------------------------------------------
        # Always close database session
        # --------------------------------------------------

        db.close()