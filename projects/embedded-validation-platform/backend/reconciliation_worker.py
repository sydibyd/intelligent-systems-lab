import json
import logging
import signal
import threading
import time

import psycopg


LOGGER = logging.getLogger("evap.reconciliation")

LOCK_ID = 82026001


class RecoveryWorker:

    def __init__(
        self,
        service,
        interval_seconds=60,
        min_age_seconds=300,
        batch_size=100,
        dry_run=True,
    ):
        if not 10 <= interval_seconds <= 3600:
            raise ValueError("Invalid interval")

        if not 60 <= min_age_seconds <= 86400:
            raise ValueError("Invalid minimum age")

        if not 1 <= batch_size <= 500:
            raise ValueError("Invalid batch size")

        self.service = service
        self.interval_seconds = interval_seconds
        self.min_age_seconds = min_age_seconds
        self.batch_size = batch_size
        self.dry_run = dry_run

        self.stop_event = threading.Event()
        self.cursor = 0

    def emit(self, event, **fields):
        LOGGER.info(json.dumps({
            "component": "reconciliation-worker",
            "event": event,
            **fields,
        }))

    def stop(self, *_):
        self.stop_event.set()

    def run_cycle(self):

        started = time.monotonic()

        metrics = {
            "scanned": 0,
            "finalized": 0,
            "eligible": 0,
            "deferred": 0,
            "conflicts": 0,
            "no_change": 0,
            "keep_running": 0,
            "errors": 0,
            "skipped": False,
            "dry_run": self.dry_run,
        }

        with psycopg.connect(
            self.service.database_url,
            autocommit=True,
        ) as conn:

            locked = conn.execute(
                "SELECT pg_try_advisory_lock(%s)",
                (LOCK_ID,),
            ).fetchone()[0]

            if not locked:
                metrics["skipped"] = True
                self.emit("cycle_skipped", **metrics)
                return metrics

            try:
                builds = conn.execute("""
                    SELECT id
                    FROM ci_builds
                    WHERE status = 'RUNNING'
                      AND created_at <= now()
                        - (%s * interval '1 second')
                      AND id > %s
                    ORDER BY id
                    LIMIT %s
                """, (
                    self.min_age_seconds,
                    self.cursor,
                    self.batch_size,
                )).fetchall()

                if not builds:
                    self.cursor = 0

                for (build_id,) in builds:

                    if self.stop_event.is_set():
                        break

                    self.cursor = build_id
                    metrics["scanned"] += 1

                    try:
                        result = self.service.reconcile_build(
                            build_id,
                            dry_run=self.dry_run,
                        )

                        action = result["action"]

                        if action == "FINALIZE":
                            metrics["eligible"] += 1

                        if result["applied"]:
                            metrics["finalized"] += 1

                        counter = {
                            "DEFER": "deferred",
                            "CONFLICT": "conflicts",
                            "NO_CHANGE": "no_change",
                            "KEEP_RUNNING": "keep_running",
                        }.get(action)

                        if counter:
                            metrics[counter] += 1

                        self.emit("build_processed", **result)

                    except Exception as exc:
                        metrics["errors"] += 1

                        self.emit(
                            "build_error",
                            build_id=build_id,
                            error_type=type(exc).__name__,
                        )

            finally:
                conn.execute(
                    "SELECT pg_advisory_unlock(%s)",
                    (LOCK_ID,),
                )

        metrics["duration_seconds"] = round(
            time.monotonic() - started, 3
        )

        self.emit("cycle_completed", **metrics)

        return metrics

    def run_forever(self):

        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)

        self.emit(
            "worker_started",
            interval_seconds=self.interval_seconds,
            dry_run=self.dry_run,
        )

        while not self.stop_event.is_set():

            try:
                self.run_cycle()

            except Exception as exc:
                self.emit(
                    "cycle_error",
                    error_type=type(exc).__name__,
                )

            self.stop_event.wait(self.interval_seconds)

        self.emit("worker_stopped")
