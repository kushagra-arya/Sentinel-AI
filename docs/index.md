# SentinelAI Documentation Index

Start here if you are new to the codebase.

## First Day Path

1. Read the root [README](../README.md) for product purpose, repository layout, and local run commands.
2. Read [Architecture](architecture.md) to understand the actual service boundaries.
3. Read [Deployment](deployment.md) if you need to run the stack through Docker Compose.
4. Read [Demo Runbook](demo-runbook.md) to operate the scripted investor/customer demo.
5. Read [Known Limitations](known-limitations.md) before making production-readiness claims.

## Engineering References

- [Architecture](architecture.md): built system architecture and service boundaries.
- [API Audit](api-audit.md): OpenAPI route documentation and access metadata audit.
- [Deployment](deployment.md): fresh-machine deployment, secrets, health checks, rollback, reset.
- [Security Audit](security-audit.md): security findings, fixes, and route-level RBAC table.
- [Demo Dataset](demo-dataset.md): synthetic incidents and near-misses.
- [Demo Runbook](demo-runbook.md): exact demo operation and talk track.
- [Demo Success Report](demo-success-report.md): pass/fail against demo success criteria.

## Frontend QA

- [Dashboard QA](frontend-qa.md)
- [Primary Views QA](frontend-primary-views-qa.md)

## API Docs

When the backend is running:

- OpenAPI JSON: `https://localhost/api/openapi.json`
- Swagger UI: `https://localhost/api/docs`
- Direct backend in development: `http://localhost:8000/api/v1/docs`

Every API route is expected to include:

- A summary.
- A meaningful description.
- A response model where applicable.
- `x-roles` OpenAPI metadata documenting route access.

This was audited during the final documentation pass.
