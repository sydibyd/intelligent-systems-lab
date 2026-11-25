import json
import time
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:8000/api"


def call(path, payload=None):
    request = Request(BASE + path, data=None if payload is None else json.dumps(payload).encode(),
                      headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=10) as response:
        return json.load(response)


payload = {"test_id": "TC-004", "idempotency_key": "ci-smoke-queue-0001"}
job = call("/jobs", payload)
assert call("/jobs", payload)["id"] == job["id"]
deadline = time.monotonic() + 90
while time.monotonic() < deadline:
    current = call("/jobs/" + str(job["id"]))
    if current["status"] == "COMPLETED":
        result = call("/executions/" + str(current["execution_id"]))
        assert result["verdict"] == "PASSED", result
        assert result["test_id"] == "TC-004"
        print("Distributed SIL execution passed")
        break
    assert current["status"] in {"QUEUED", "RUNNING"}, current
    time.sleep(2)
else:
    raise AssertionError("Worker did not complete within deadline")
