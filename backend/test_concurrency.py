import requests
import concurrent.futures
import time


URL = "http://127.0.0.1:8000/parse"

REQUEST_COUNT = 10


def send_request(request_number):

    start_time = time.time()

    try:

        response = requests.post(
            URL,
            json={
                "text": "Schedule a meeting tomorrow at 10 AM"
            },
            timeout=60
        )

        elapsed = time.time() - start_time

        return {
            "request": request_number,
            "status_code": response.status_code,
            "time": round(elapsed, 2),
            "success": response.status_code == 200
        }

    except Exception as e:

        elapsed = time.time() - start_time

        return {
            "request": request_number,
            "status_code": "ERROR",
            "time": round(elapsed, 2),
            "success": False,
            "error": str(e)
        }


print(f"Starting {REQUEST_COUNT} concurrent requests...")

start = time.time()

with concurrent.futures.ThreadPoolExecutor(
    max_workers=REQUEST_COUNT
) as executor:

    futures = [
        executor.submit(send_request, i + 1)
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
    1 for result in results
    if result["success"]
)

failed = REQUEST_COUNT - successful

print(f"Successful: {successful}")
print(f"Failed: {failed}")
print(f"Total time: {round(total_time, 2)} seconds")