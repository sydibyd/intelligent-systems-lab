# EVAP v1.0.0-rc.1 — Local acceptance report

Date: 2026-11-25
Tested commit: d0e7b4301cfae97b99a67c2b8f40fc1368b85f40
CI run: 45624951105 (SUCCESS, previously verified)
Decision: PASS for scoped local acceptance; not production approval.

## Evidence

Operator-provided terminal results and Grafana screenshots from isolated Compose project evap-rc1, detached tagged worktree. Six services: PostgreSQL, FastAPI, React/nginx, SIL worker, Prometheus, Grafana. Loopback API 8100, UI 8180, Prometheus 9090, Grafana 3000.

| Gate | Observed result |
|---|---|
| Deployment | API healthy, database connected, six services started |
| Authentication | Web login successful; 12/12 HTTP RBAC checks passed |
| SRS | 12 requirements, 12 test cases, 12 mapped, 100% mapping |
| SIL queue | TC-004, TC-008, TC-009, TC-011 all PASSED; jobs 1,3,5,7 |
| Idempotency | 4/4 duplicate submissions returned same job IDs; four executions persisted |
| Dashboard | 4 passed, 0 failed, 0 errors; 100% pass rate on executed tests; 4/12 execution coverage |
| AI safe mode | 5/5 checks passed; disabled generation HTTP 503, no drafts created, execution counts unchanged |
| Monitoring | Prometheus up=1, active workers=1; Grafana six provisioned panels displaying metrics |

## Findings and deployment notes

Prometheus initially failed to read the bearer secret because its process UID/GID 65534 could not read a host file owned by UID 1000 with mode 0600. In this isolated installation, changing ownership to 65534:65534 and mode to 0400 restored authenticated scraping without restarting containers. Verify actual container UID and host mapping before applying this approach elsewhere. Use dedicated least-privilege monitoring credentials and protected secret storage in production; the lab reused a viewer identity.

Two acceptance-script errors were corrected without changing application code: SRS payload did not expose an id key; disabled AI returned 503 rather than the initially expected 502. Corrected checks passed.

API health still reported version 0.3.0; release metadata needs alignment. Only one SIL worker was exercised locally. Four SIL simulations do not establish real ECU behavior or full requirements execution coverage.

## Remaining release gates

- Live Claude API generation and independent review with approved non-sensitive inputs; mocked CI coverage is not live provider validation.
- Real Jenkins authenticated pipeline and reconciliation runtime qualification.
- HIL hardware validation, multi-worker resilience and production load/fault testing.
- Production security review, scoped credentials, TLS, backup/restore, operational alert delivery and deployment qualification.
- Implement or qualify the remaining eight referenced test cases.

No production deployment or main merge is authorized by this report. The RC1 tag remains unchanged. This document records observed local evidence, not an independent audit or certification.
