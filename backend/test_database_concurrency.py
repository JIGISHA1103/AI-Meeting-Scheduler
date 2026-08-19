import concurrent.futures
import time
import uuid

from app.database.database import SessionLocal
from app.database.models import MeetingRequest


REQUEST_COUNT = 10


def create_request(request_number):

    start_time = time.time()

    request_id = str(uuid.uuid4())

    db = SessionLocal()

    try:

        request = MeetingRequest(
            request_id=request_id,
            user_input=f"Concurrent test request {request_number}",
            status="processing"
        )

        db.add(request)
        db.commit()
        db.refresh(request)

        request.status = "success"
        request.completed_at = __import__("datetime").datetime.utcnow()

        db.commit()

        elapsed = time.time() - start_time

        return {
            "request": request_number,
            "request_id": request_id,
            "status": "success",
            "time": round(elapsed, 3)
        }

    except Exception as e:

        db.rollback()

        elapsed = time.time() - start_time

        return {
            "request": request_number,
            "request_id": request_id,
            "status": "error",
            "time": round(elapsed, 3),
            "error": str(e)
        }

    finally:

        db.close()


print(
    f"Starting {REQUEST_COUNT} concurrent "
    "database requests..."
)

start = time.time()

with concurrent.futures.ThreadPoolExecutor(
    max_workers=REQUEST_COUNT
) as executor:

    futures = [
        executor.submit(
            create_request,
            i + 1
        )
        for i in range(REQUEST_COUNT)
    ]

    results = [
        future.result()
        for future in futures
    ]


total_time = time.time() - start


print("\n========== RESULTS ==========")

for result in results:
    print(result)

print("=============================")

successful = sum(
    1
    for result in results
    if result["status"] == "success"
)

failed = REQUEST_COUNT - successful

print(f"Successful: {successful}")
print(f"Failed: {failed}")
print(
    f"Total time: {round(total_time, 3)} seconds"
)