"""Standalone SIL worker. Hardware execution is deliberately disabled."""
import logging
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid

from execution_api import ALLOWED_TESTS, SIL_ROOT, classify_pytest_result
from execution_queue import ExecutionQueue

LOG = logging.getLogger(__name__)


def execute_sil(test_id):
    start = time.monotonic()
    if test_id not in ALLOWED_TESTS:
        return "ERROR", 0, "Unregistered SIL test"
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             ALLOWED_TESTS[test_id]],
            cwd=SIL_ROOT, capture_output=True, text=True, errors="replace",
            timeout=30, check=False,
            env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1",
                 "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "LANG": "C.UTF-8"},
        )
        verdict = classify_pytest_result(result.returncode)
        logs = result.stdout + "\n" + result.stderr
    except subprocess.TimeoutExpired:
        verdict, logs = "ERROR", "SIL execution timed out"
    except OSError:
        verdict, logs = "ERROR", "SIL runner unavailable"
    return verdict, round(time.monotonic() - start, 3), logs[:20000]


class Worker:
    def __init__(self, queue, worker_id, runner=execute_sil):
        self.queue = queue
        self.worker_id = worker_id
        self.runner = runner
        self.stop = threading.Event()

    def cycle(self):
        self.queue.expire()
        if self.stop.is_set():
            return False
        job = self.queue.claim(self.worker_id, "SIL", 120)
        if job is None:
            return False
        verdict, duration, logs = self.runner(job["test_id"])
        if not self.queue.finish(job["id"], job["lease_token"], verdict, duration, logs):
            LOG.warning("Job %s lease lost; result discarded", job["id"])
        return True

    def run(self):
        while not self.stop.is_set():
            try:
                with self.queue.connect() as conn:
                    conn.execute("""
                        INSERT INTO worker_heartbeats(worker_id,environment)
                        VALUES (%s,'SIL') ON CONFLICT(worker_id)
                        DO UPDATE SET last_seen=now()
                    """, (self.worker_id,))
                    conn.execute("DELETE FROM worker_heartbeats WHERE last_seen < now()-interval '7 days'")
                if not self.cycle():
                    self.stop.wait(2)
            except Exception:
                LOG.error("Worker cycle failed; pending lease will expire")
                self.stop.wait(5)


def main():
    logging.basicConfig(level=logging.INFO)
    if os.getenv("EVAP_WORKER_ENVIRONMENT", "SIL") != "SIL":
        raise SystemExit("HIL execution requires a qualified hardware adapter")
    worker = Worker(ExecutionQueue(os.environ["DATABASE_URL"]),
                    socket.gethostname() + "-" + uuid.uuid4().hex)
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: worker.stop.set())
    worker.run()


if __name__ == "__main__":
    main()
