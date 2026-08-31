from datetime import datetime

from app.database.database import SessionLocal
from app.database.models import MeetingRequest as MeetingRequestDB
from app.services.scheduling_service import schedule_meeting
from celery_app import celery_app


@celery_app.task
def process_meeting_request(user_input: str, request_id: str):
    """
    Process a meeting scheduling request asynchronously.

    The task:
    1. Runs the existing scheduling workflow.
    2. Updates the PostgreSQL request status.
    3. Stores completion time.
    4. Stores errors if the workflow fails.

    The complete scheduling result is returned to Celery.
    Celery stores that result in Redis.
    """

    print(f"[{request_id}] Celery task started")

    db = SessionLocal()

    try:
        # --------------------------------------------------
        # Run existing scheduling workflow
        # --------------------------------------------------

        result = schedule_meeting(
            user_input,
            request_id
        )

        print(
            f"[{request_id}] Scheduling result:"
        )
        print(result)

        # --------------------------------------------------
        # Find request in database
        # --------------------------------------------------

        db_request = (
            db.query(MeetingRequestDB)
            .filter(
                MeetingRequestDB.request_id == request_id
            )
            .first()
        )

        # --------------------------------------------------
        # Update request status
        # --------------------------------------------------

        if db_request:
            db_request.status = result.get(
                "status",
                "success"
            )

            db_request.completed_at = datetime.utcnow()

            # If the scheduling workflow returned an error,
            # keep its message in the existing error_message column.
            if result.get("status") == "error":
                db_request.error_message = result.get(
                    "message"
                )

            db.commit()

        print(
            f"[{request_id}] Celery task completed"
        )

        # IMPORTANT:
        # This complete result is stored by Celery in Redis.
        return result

    # ==================================================
    # Runtime Error
    # ==================================================

    except RuntimeError as e:

        error_message = str(e)

        print(
            f"[{request_id}] Celery task failed: "
            f"{error_message}"
        )

        db_request = (
            db.query(MeetingRequestDB)
            .filter(
                MeetingRequestDB.request_id == request_id
            )
            .first()
        )

        if db_request:

            db_request.status = "error"

            db_request.error_message = error_message

            db_request.completed_at = datetime.utcnow()

            db.commit()

        # Preserve existing Gemini quota behavior.

        if "Gemini API quota exceeded" in error_message:

            return {
                "status": "error",
                "error_type": "quota_exceeded",
                "message": (
                    "Gemini API quota exceeded. "
                    "Please try again later."
                )
            }

        return {
            "status": "error",
            "message": error_message
        }

    # ==================================================
    # General Exception
    # ==================================================

    except Exception as e:

        error_message = str(e)

        print(
            f"[{request_id}] Celery task failed: "
            f"{error_message}"
        )

        db_request = (
            db.query(MeetingRequestDB)
            .filter(
                MeetingRequestDB.request_id == request_id
            )
            .first()
        )

        if db_request:

            db_request.status = "error"

            db_request.error_message = error_message

            db_request.completed_at = datetime.utcnow()

            db.commit()

        return {
            "status": "error",
            "message": error_message
        }

    finally:

        db.close()