# EVAP v1.0 release candidate checklist

Do not deploy to production until all mandatory gates are evidenced.

## Isolated deployment
Use a separate Compose project on a dedicated test host with free ports.
Set DB_PASSWORD to a random URL-safe secret. Set EVAP_AUTH_MODE=required.
Set EVAP_IDENTITIES_JSON to a JSON array of named roles and SHA-256 digests
of independently generated high-entropy bearer tokens. Never commit tokens.
Run docker compose -p evap-rc up -d --build --wait.
Verify /api/health and authenticate through the UI. Keep ports loopback-only;
use a separately qualified TLS gateway for remote access.

## Monitoring
Set EVAP_METRICS_TOKEN_FILE to a protected file containing a dedicated token
and GRAFANA_ADMIN_PASSWORD to a strong password.
Run docker compose -p evap-rc -f docker-compose.yml -f compose.monitoring.yml up -d.
Check Prometheus target health and Grafana datasource.
Alert delivery requires separate configuration.

## Release gates
- Backend, frontend, migrations, Docker smoke and distributed SIL CI green.
- Authenticated HTTP role tests and independent AI review tests green.
- Backup and restore rehearsal, dependency review, secret handling and TLS review.
- Real Claude calls only with authorized non-confidential requirements.
- HIL disabled until hardware-specific safety qualification.
- Recovery worker remains lab-only until production qualification.
- No automatic execution of AI-generated drafts.
- No production release or main merge without owner approval.

## Rollback
Retain the previous image versions and verified database backup.
Stop new submissions and drain workers before maintenance.
Do not downgrade schema blindly; restore a tested backup if necessary.
Never use down -v against an operational database.
