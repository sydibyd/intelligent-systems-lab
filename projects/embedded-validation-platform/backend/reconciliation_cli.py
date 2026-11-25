import argparse
import getpass
import json
import os
from urllib.parse import urlsplit

from jenkins_client import JenkinsClient
from reconciliation_service import ReconciliationService


def main():
    parser = argparse.ArgumentParser(
        description="EVAP Reconciliation CLI"
    )

    mode = parser.add_mutually_exclusive_group()

    mode.add_argument(
        "--dry-run",
        action="store_true",
    )

    mode.add_argument(
        "--apply",
        action="store_true",
    )

    parser.add_argument(
        "--build-id",
        type=int,
        action="append",
    )

    args = parser.parse_args()

    database_url = os.environ["DATABASE_URL"]
    database = urlsplit(database_url)

    if (
        database.hostname != "evap-migration-test-db"
        or database.path != "/evap_fresh"
        or database.query
    ):
        raise SystemExit(
            "SAFETY BLOCK: isolated database required"
        )

    if args.apply and not args.build_id:
        raise SystemExit(
            "SAFETY BLOCK: explicit build IDs required"
        )

    if args.build_id and any(
        build_id <= 0 for build_id in args.build_id
    ):
        raise SystemExit("Invalid build ID")

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

    dry_run = not args.apply

    if args.apply:
        confirmation = input(
            "Type APPLY-LAB to confirm: "
        )

        if confirmation != "APPLY-LAB":
            raise SystemExit("Operation cancelled")

    if args.build_id:
        results = [
            service.reconcile_build(
                build_id,
                dry_run=dry_run,
            )
            for build_id in dict.fromkeys(args.build_id)
        ]
    else:
        results = service.reconcile_pending(
            min_age_seconds=300,
            limit=100,
            dry_run=dry_run,
        )

    print("\nEVAP RECONCILIATION REPORT")
    print("=" * 60)

    for result in results:
        print(json.dumps(result, indent=2))

    print("=" * 60)
    print("Mode:", "DRY-RUN" if dry_run else "APPLY")
    print("Scanned:", len(results))

    for action in (
        "FINALIZE",
        "DEFER",
        "NO_CHANGE",
        "CONFLICT",
        "KEEP_RUNNING",
    ):
        print(
            f"{action}:",
            sum(r["action"] == action for r in results),
        )

    print(
        "Database updates:",
        sum(r["applied"] for r in results),
    )


if __name__ == "__main__":
    main()
