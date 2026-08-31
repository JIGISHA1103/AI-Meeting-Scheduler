from celery import Celery


celery_app = Celery(
    "meeting_ai",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)


celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=False
)


celery_app.autodiscover_tasks(["app"])


# Load safe concurrency demo task
import app.tasks_demo