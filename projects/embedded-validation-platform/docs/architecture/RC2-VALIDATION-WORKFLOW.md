# RC2 — Requirements-driven continuous validation

Status: proposed design, not implemented. RC1 tag remains unchanged.

## User workflow
1. Connect a BMS Git repository and configure trusted branches, build command and SIL adapter.
2. Import requirements-only XLSX into a versioned baseline; preview changes and retain historical baselines.
3. Define one or more test cases per requirement, including preconditions, inputs, expected outputs and priority.
4. Define a test script in a web editor or link a versioned script from a trusted Git repository. Save drafts and require independent approval before execution.
5. Enable automatic validation on pushes to configured branches. Jenkins or GitHub Actions checks out the exact BMS commit, builds the actual software under test, runs the approved test baseline in an isolated runner, and publishes results to EVAP.
6. Review commit-specific verdicts, logs, coverage and quality gate.

## UI
Overview; Requirements; Test Design (cases and scripts); CI/CD Integration; Validation Results; Settings. Keep technical monitoring separate. AI assistance optional, never required.

## Architecture decisions proposed
- PostgreSQL versioned requirements, cases, script revisions, approvals, project/repository bindings and validation runs.
- Dynamic discovery of approved tests instead of hardcoded frontend/backend allowlists.
- Distinguish test script from BMS software under test. Require an explicit SIL adapter and build artifact for the exact Git commit; no fabricated Python model as proof of BMS validation.
- Authenticated CI event ingestion, deduplication by repository/commit/baseline, explicit branch filters and visible build failures. Git push is the trigger, not unsaved local edits.
- Do not execute user-entered Python in the API or existing privileged worker. Separate disposable runner with no Docker socket, secrets or host mounts, restricted network, non-root identity, resource/time limits and approved immutable script revisions. Runner isolation requires security qualification.
- Preserve RC1 and historical evidence. No automatic production deployment or main merge.

## Implementation increments
1. Versioned requirement import and manual case design.
2. Script editor, revision registry, approval and dynamic test discovery.
3. Isolated SIL execution and BMS build/adapter contract.
4. Git-triggered CI pipeline and commit-level quality gate.
5. End-to-end acceptance with synthetic BMS repository: passing commit, regression commit, corrected commit, duplicate event and unauthorized script rejection.

## Open integration input
Actual BMS repository URL, language/build system, branch policy and SIL interface are not yet supplied. Use a clearly labeled synthetic BMS fixture for development until these are known. No real BMS validation claim until integrated and tested.
