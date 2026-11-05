# EVAP — Embedded Validation Automation Platform

## A Universal CI/CD Validation Platform for Embedded Software Systems

### System Architecture

```mermaid
flowchart TB
    SRS["Excel Software Requirements"] --> REQ

    subgraph DOCKER["Docker Platform"]
        UI["React Frontend"]
        API["FastAPI Backend"]
        REQ["Requirements Engine"]
        AI["AI Engineering Service"]
        DB[("PostgreSQL")]
        REDIS[("Redis")]
        WORKER["Test Orchestrator"]
        SIL["SIL Test Runner / pytest"]
        REPORT["Validation & Reporting"]

        UI --> API
        API --> REQ
        REQ --> DB
        API --> AI
        API --> REDIS
        REDIS --> WORKER
        WORKER --> SIL
        SIL --> REPORT
        REPORT --> DB
    end

    GIT["GitHub Repository"] --> CI["Jenkins CI/CD"]
    CI --> API
    CI --> WORKER

    WORKER --> HIL["External HIL Agent"]
    HIL --> HW["ECU / dSPACE / CANoe"]
    REPORT --> UI
```

### Core Capabilities

- Requirements-driven validation
- Automated test case management
- Docker-based execution infrastructure
- Jenkins CI/CD integration
- SIL / PIL / HIL test orchestration
- AI-assisted test engineering
- End-to-end requirements traceability
- Centralized validation reporting

### Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React / TypeScript |
| Backend | Python / FastAPI |
| Infrastructure | Docker / Docker Compose |
| CI/CD | Jenkins / GitHub |
| Database | PostgreSQL |
| Task Queue | Redis |
| Testing | pytest |
| AI | OpenAI / Claude |
| Embedded Validation | SIL / PIL / HIL |

### Architecture Principles

- Modular and scalable architecture
- Hardware-independent test execution
- Reproducible testing environments
- Requirements-to-results traceability
- Deterministic validation verdicts
- Human review of AI-generated tests
- Secure integration with external test benches
