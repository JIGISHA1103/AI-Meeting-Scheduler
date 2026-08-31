import concurrent.futures
import time
import uuid

from app.tasks_demo import demo_meeting_request


REQUEST_COUNT = 10


def send_request(request_number):

    request_id = str(uuid.uuid4())

    start_time = time.time()

    task = demo_meeting_request.delay(
        f"Demo meeting request {request_number}",
        request_id
    )

    elapsed = time.time() - start_time

    return {
        "request": request_number,
        "request_id": request_id,
        "task_id": task.id,
        "queue_time": round(elapsed, 3)
    }


print(
    "\n=========================================="
)

print(
    f"Submitting {REQUEST_COUNT} "
    "concurrent requests to Celery..."
)

print(
    "==========================================\n"
)


start = time.time()


with concurrent.futures.ThreadPoolExecutor(
    max_workers=REQUEST_COUNT
) as executor:

    futures = [
        executor.submit(
            send_request,
            i + 1
        )
        for i in range(REQUEST_COUNT)
    ]

    results = [
        future.result()
        for future in futures
    ]


total_time = time.time() - start


print(
    "\n========== QUEUE RESULTS =========="
)


for result in results:

    print(
        f"Request {result['request']} | "
        f"Request ID: {result['request_id']} | "
        f"Task ID: {result['task_id']} | "
        f"Queue time: {result['queue_time']}s"
    )


print(
    "===================================="
)

print(
    f"\nSubmitted: {REQUEST_COUNT}"
)

print(
    f"Total submission time: "
    f"{round(total_time, 3)} seconds"
)

print(
    "\nAll requests have been queued."
)

print(
    "Check the Celery worker terminal "
    "to see background processing."
)