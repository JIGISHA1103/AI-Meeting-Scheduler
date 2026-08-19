from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.ai.parser import parse_meeting_request
from app.calendar.calendar_service import (
    check_availability,
    create_calendar_event
)


# --------------------------------------------------
# Application timezone
# --------------------------------------------------

IST = ZoneInfo("Asia/Kolkata")


# --------------------------------------------------
# Schedule Meeting
# --------------------------------------------------

def schedule_meeting(user_input: str, request_id: str):
    """
    Complete meeting scheduling workflow:

    1. Parse the user's request using Gemini.
    2. Convert date/time into timezone-aware datetime objects.
    3. Check Google Calendar availability.
    4. Create the calendar event if the slot is free.
    5. Add participants as Google Calendar attendees.
    """

    # --------------------------------------------------
    # Step 1: Parse meeting request using Gemini
    # --------------------------------------------------

    print(f"[{request_id}] Parsing meeting request")

    meeting = parse_meeting_request(user_input)

    print(f"[{request_id}] Parsed meeting:")
    print(meeting)


    # --------------------------------------------------
    # Step 2: Validate intent
    # --------------------------------------------------

    if meeting.get("intent") != "schedule_meeting":
        return {
            "status": "error",
            "message": "The request is not a meeting scheduling request."
        }


    # --------------------------------------------------
    # Step 3: Extract meeting details
    # --------------------------------------------------

    title = meeting.get("title", "Meeting")
    date = meeting.get("date")
    time = meeting.get("time")
    duration = meeting.get("duration", 60)

    # Get participants extracted by Gemini
    participants = meeting.get("participants", [])

    # Make sure participants is always a list
    if not isinstance(participants, list):
        participants = []


    # --------------------------------------------------
    # Validate date and time
    # --------------------------------------------------

    if not date or not time:
        return {
            "status": "error",
            "message": "Meeting date or time is missing."
        }


    # --------------------------------------------------
    # Step 4: Convert date and time into datetime
    # --------------------------------------------------

    try:

        start_time = datetime.fromisoformat(
            f"{date}T{time}"
        ).replace(tzinfo=IST)

    except ValueError:

        return {
            "status": "error",
            "message": (
                "Unable to understand the meeting date/time. "
                f"Received date='{date}', time='{time}'."
            )
        }


    # --------------------------------------------------
    # Step 5: Calculate end time
    # --------------------------------------------------

    end_time = start_time + timedelta(
        minutes=int(duration)
    )


    print(f"[{request_id}] Meeting time:")
    print("Start:", start_time)
    print("End:", end_time)


    # --------------------------------------------------
    # Step 6: Check Google Calendar availability
    # --------------------------------------------------

    print(f"[{request_id}] Checking calendar availability")

    busy_periods = check_availability(
        start_time,
        end_time
    )


    # --------------------------------------------------
    # Step 7: Check for conflicts
    # --------------------------------------------------

    if busy_periods:

        print(f"[{request_id}] Calendar conflict detected")

        return {
            "status": "conflict",
            "message": "The requested time slot is already busy.",
            "busy_periods": busy_periods
        }


    # --------------------------------------------------
    # Step 8: Create event description
    # --------------------------------------------------

    if participants:

        description = (
            f"Participants: "
            f"{', '.join(participants)}"
        )

    else:

        description = "No participants specified."


    # --------------------------------------------------
    # Step 9: Create Google Calendar event
    # --------------------------------------------------

    print(f"[{request_id}] Creating calendar event")

    event = create_calendar_event(
        summary=title,
        start_time=start_time,
        end_time=end_time,
        description=description,
        participants=participants
    )


    # --------------------------------------------------
    # Step 10: Return result
    # --------------------------------------------------

    print(f"[{request_id}] Meeting scheduled successfully")

    return {
        "status": "success",
        "message": "Meeting scheduled successfully.",
        "meeting": meeting,
        "event": event
    }