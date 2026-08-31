import time

from celery_app import celery_app


@celery_app.task
def demo_meeting_request(
    user_input: str,
    request_id: str
):
    """
    Safe concurrency demo task.

    This simulates meeting processing without
    creating a Google Calendar event.
    """

    print(
        f"[DEMO-{request_id}] "
        f"Task started"
    )

    print(
        f"[DEMO-{request_id}] "
        f"Processing: {user_input}"
    )

    # Simulate background processing
    time.sleep(2)

    print(
        f"[DEMO-{request_id}] "
        f"Task completed"
    )

    return {
        "request_id": request_id,
        "status": "success",
        "message": "Demo request processed successfully"
    }