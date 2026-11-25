import getpass
import json
import os
from urllib.parse import urlsplit

from jenkins_client import JenkinsClient
from reconciliation_service import ReconciliationService


def main():

    database_url = os.environ["DATABASE_URL"]
    database = urlsplit(database_url)

    if (
        database.hostname != "evap-migration-test-db"
        or database.path != "/evap_fresh"
    ):
        raise SystemExit(
            "SAFETY BLOCK: isolated database required"
        )

    username = input("Jenkins username: ")
    token = getpass.getpass("Jenkins API token: ")

    client = JenkinsClient(
        base_url="http://127.0.0.1:8082",
        username=username,
        api_token=token,
        allow_loopback_http=True,
    )

    trusted_clients = {
        (
            "jenkins-reliability",
            "EVAP-TRACEABILITY-RELIABILITY",
        ): client,
        (
            "jenkins-reliability",
            "EVAP-INTERRUPTION-TEST",
        ): client,
    }

    service = ReconciliationService(
        database_url,
        trusted_clients,
    )

    results = service.reconcile_pending(
        min_age_seconds=300,
        limit=100,
        dry_run=True,
    )

    print("\nEVAP RECONCILIATION REPORT")
    print("=" * 60)

    for result in results:
        print(json.dumps(result, indent=2))

    eligible = sum(
        result["action"] == "FINALIZE"
        for result in results
    )

    deferred = sum(
        result["action"] == "DEFER"
        for result in results
    )

    print("=" * 60)
    print("Mode              : DRY-RUN")
    print(f"Scanned builds    : {len(results)}")
    print(f"Eligible recovery : {eligible}")
    print(f"Deferred builds   : {deferred}")
    print("Database updates  : 0")


if __name__ == "__main__":
    main()
