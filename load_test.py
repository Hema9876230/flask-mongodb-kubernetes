
import time
import urllib.request
import urllib.error
import concurrent.futures
import threading
from collections import Counter

URL = "http://localhost:5001/data"
DURATION = 180
WORKERS = 50

successful = 0
failed = 0
errors = Counter()
lock = threading.Lock()


def send_request():
    global successful, failed

    deadline = time.monotonic() + DURATION

    while time.monotonic() < deadline:
        try:
            req = urllib.request.Request(
                URL,
                headers={"User-Agent": "Kubernetes-Load-Test"}
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                response.read()

                with lock:
                    successful += 1

        except urllib.error.HTTPError as e:
            with lock:
                failed += 1
                errors[f"HTTP {e.code}"] += 1

        except Exception as e:
            with lock:
                failed += 1
                errors[type(e).__name__] += 1


print("Starting diagnostic load test...")
print(f"Workers: {WORKERS}")
print(f"Duration: {DURATION} seconds")

start = time.monotonic()

with concurrent.futures.ThreadPoolExecutor(
    max_workers=WORKERS
) as executor:

    futures = [
        executor.submit(send_request)
        for _ in range(WORKERS)
    ]

    concurrent.futures.wait(futures)

elapsed = time.monotonic() - start

total = successful + failed

print("\nDIAGNOSTIC LOAD TEST RESULTS")
print("----------------------------")
print(f"Duration: {elapsed:.2f} seconds")
print(f"Successful: {successful}")
print(f"Failed: {failed}")
print(f"Success rate: {successful / total * 100:.2f}%")
print(f"Successful RPS: {successful / elapsed:.2f}")

print("\nERROR BREAKDOWN:")

for error, count in errors.most_common():
    print(f"{error}: {count}")
