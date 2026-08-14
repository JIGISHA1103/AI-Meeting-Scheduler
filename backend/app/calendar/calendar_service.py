import os
import json
import uuid
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


# --------------------------------------------------
# Project base directory
# --------------------------------------------------

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)


# --------------------------------------------------
# Google OAuth token file
# --------------------------------------------------

TOKEN_FILE = os.path.join(
    BASE_DIR,
    "token.json"
)


# --------------------------------------------------
# Create Google Calendar Service
# --------------------------------------------------

def get_calendar_service():

    if not os.path.exists(TOKEN_FILE):
        raise FileNotFoundError(
            "token.json not found. Please login with Google first."
        )

    with open(TOKEN_FILE, "r") as token_file:
        token_data = json.load(token_file)

    credentials = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes")
    )

    service = build(
        "calendar",
        "v3",
        credentials=credentials
    )

    return service


# --------------------------------------------------
# Check Google Calendar Availability
# --------------------------------------------------

def check_availability(
    start_time: datetime,
    end_time: datetime
):
    """
    Check whether the primary Google Calendar
    has any busy periods between start_time
    and end_time.
    """

    service = get_calendar_service()

    # Convert timezone-aware datetime to UTC
    start_utc = start_time.astimezone(timezone.utc)
    end_utc = end_time.astimezone(timezone.utc)

    body = {
        "timeMin": start_utc.isoformat().replace("+00:00", "Z"),
        "timeMax": end_utc.isoformat().replace("+00:00", "Z"),
        "items": [
            {
                "id": "primary"
            }
        ]
    }

    print("\n========== FREEBUSY REQUEST ==========")
    print(body)
    print("======================================\n")

    result = service.freebusy().query(
        body=body
    ).execute()

    busy_periods = result[
        "calendars"
    ][
        "primary"
    ][
        "busy"
    ]

    return busy_periods


# --------------------------------------------------
# Create Google Calendar Event
# --------------------------------------------------

def create_calendar_event(
    summary: str,
    start_time: datetime,
    end_time: datetime,
    description: str = "",
    participants: list = None
):
    """
    Create a Google Calendar event with:

    - Meeting title
    - Start and end time
    - Description
    - Participants
    - Google Meet conference
    - Email invitations
    """

    service = get_calendar_service()

    # --------------------------------------------------
    # Basic event information
    # --------------------------------------------------

    event = {
        "summary": summary,
        "description": description,

        "start": {
            "dateTime": start_time.isoformat(),
            "timeZone": "Asia/Kolkata"
        },

        "end": {
            "dateTime": end_time.isoformat(),
            "timeZone": "Asia/Kolkata"
        },

        # --------------------------------------------------
        # Request Google Meet conference creation
        # --------------------------------------------------

        "conferenceData": {
            "createRequest": {
                "requestId": str(uuid.uuid4()),
                "conferenceSolutionKey": {
                    "type": "hangoutsMeet"
                }
            }
        }
    }

    # --------------------------------------------------
    # Add participants as Google Calendar attendees
    # --------------------------------------------------

    if participants:

        event["attendees"] = [
            {
                "email": participant
            }
            for participant in participants
        ]

    # --------------------------------------------------
    # Display event information before creation
    # --------------------------------------------------

    print("\n========== CALENDAR EVENT ==========")
    print("Title:", summary)
    print("Start:", start_time)
    print("End:", end_time)
    print("Participants:", participants)
    print("Google Meet: Requested")
    print("====================================\n")

    # --------------------------------------------------
    # Create Google Calendar event
    # --------------------------------------------------

    created_event = service.events().insert(
        calendarId="primary",
        body=event,
        sendUpdates="all",
        conferenceDataVersion=1
    ).execute()

    # --------------------------------------------------
    # Extract Google Meet link
    # --------------------------------------------------

    conference_data = created_event.get(
        "conferenceData",
        {}
    )

    entry_points = conference_data.get(
        "entryPoints",
        []
    )

    meet_link = None

    for entry_point in entry_points:

        if entry_point.get("entryPointType") == "video":

            meet_link = entry_point.get("uri")
            break

    # --------------------------------------------------
    # Display Google Meet link
    # --------------------------------------------------

    print("\n========== GOOGLE MEET ==========")
    print("Meet Link:", meet_link)
    print("=================================\n")

    # --------------------------------------------------
    # Return event information
    # --------------------------------------------------

    return {
        "event_id": created_event.get("id"),

        "event_link": created_event.get(
            "htmlLink"
        ),

        "meet_link": meet_link,

        "event_summary": created_event.get(
            "summary"
        ),

        "start": created_event.get(
            "start"
        ),

        "end": created_event.get(
            "end"
        ),

        "attendees": created_event.get(
            "attendees",
            []
        )
    }