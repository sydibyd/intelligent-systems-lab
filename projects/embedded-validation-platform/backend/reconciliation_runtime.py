import argparse
import getpass
import logging
import os
from urllib.parse import urlsplit

from jenkins_client import JenkinsClient
from reconciliation_service import ReconciliationService
from reconciliation_worker import RecoveryWorker


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    database_url = os.environ["DATABASE_URL"]
    database = urlsplit(database_url)
    if (database.hostname != "evap-migration-test-db"
            or database.path != "/evap_fresh" or database.query):
        raise SystemExit("SAFETY BLOCK: isolated database required")
    username = os.getenv("JENKINS_USERNAME") or input("Jenkins username: ")
    token = getpass.getpass("Jenkins API token: ")
    if not username or not token:
        raise SystemExit("Jenkins credentials required")
    client = JenkinsClient(
        base_url="http://127.0.0.1:8080", username=username,
        api_token=token, allow_loopback_http=True,
    )
    trusted = {
        ("jenkins-reliability", name): client
        for name in ("EVAP-TRACEABILITY-RELIABILITY", "EVAP-INTERRUPTION-TEST")
    }
    worker = RecoveryWorker(
        ReconciliationService(database_url, trusted),
        interval_seconds=int(os.getenv("EVAP_RECOVERY_INTERVAL", "60")),
        min_age_seconds=int(os.getenv("EVAP_RECOVERY_MIN_AGE", "300")),
        batch_size=int(os.getenv("EVAP_RECOVERY_BATCH_SIZE", "100")),
        dry_run=True,
    )
    if args.once:
        if worker.run_cycle()["errors"]:
            raise SystemExit(1)
    else:
        worker.run_forever()


if __name__ == "__main__":
    main()
