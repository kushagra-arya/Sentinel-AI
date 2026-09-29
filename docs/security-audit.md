# SentinelAI Backend Security Audit

Date: 2026-07-08

Scope: FastAPI backend, authentication/RBAC, input validation, audit logging, report export boundaries, rate limiting, and Nginx edge configuration.

## Findings And Fixes

| Severity | Finding | Fix applied |
| --- | --- | --- |
| High | JWT decoding trusted the configured algorithm list but did not explicitly reject mismatched token `alg` headers. | Added header `alg` equality check, issuer and audience claims, and settings validation restricting algorithms to HS256/HS384/HS512. |
| High | Auth and Chat APIs had no rate limiting. | Added process-local sliding-window limiter and applied it to `/auth/login`, `/auth/refresh`, `/chat/query`, and `/chat/incidents/{incident_id}/explain`. |
| High | Nginx was HTTP-only and lacked browser security headers. | Added HTTP-to-HTTPS redirect, TLS server, HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, and Permissions-Policy. Docker Compose now exposes 443 and creates an ephemeral self-signed demo cert at container startup. |
| Medium | Several boundary schemas accepted unbounded strings and free-form route identifiers. | Added max lengths, regex constraints, numeric ranges, enum/literal constraints, and viewport validation across auth, chat, map, risk, notification, and report routes. |
| Medium | Report filenames were built directly from incident IDs. The API path did not use a path converter, but service-level calls could still create unsafe names. | Added `_safe_export_filename` and route `Path` validation to reject traversal-capable identifiers. |
| Medium | Retrieved documents could surface prompt-injection instructions as answer text. | Added retrieved-excerpt filtering for common instruction-injection markers and kept assistant behavior retrieval-only with citations. |
| Medium | Chat history writes were not separately audit logged. | Added `chat_turn_persisted` audit records containing mode, grounded status, citation count, and question length without storing raw prompts in audit metadata. |
| Low | Failed refresh-token attempts were not consistently audited. | Added `refresh_failed` audit records for malformed, missing, revoked, expired, and inactive-user refresh attempts. |
| Low | Password hashing used bcrypt through Passlib but did not pin cost in code. | Set bcrypt work factor to 12 and added regression coverage. |

## Route-By-Route RBAC Audit

| Method | Route | Roles |
| --- | --- | --- |
| GET | `/api/v1/health` | Public |
| GET | `/api/v1/health/ready` | Public |
| POST | `/api/v1/auth/login` | Public, rate limited |
| POST | `/api/v1/auth/refresh` | Public, rate limited |
| POST | `/api/v1/auth/logout` | Authenticated user |
| GET | `/api/v1/dashboard/summary` | Admin, Safety Officer, Supervisor, Compliance Officer, Viewer |
| POST | `/api/v1/notifications` | Admin, Safety Officer, Supervisor |
| GET | `/api/v1/notifications` | Admin, Safety Officer, Supervisor, Compliance Officer, Viewer |
| POST | `/api/v1/notifications/{notification_id}/read` | Admin, Safety Officer, Supervisor, Compliance Officer, Viewer |
| POST | `/api/v1/risk/rules/evaluate` | Admin, Safety Officer, Supervisor |
| POST | `/api/v1/risk/classify` | Admin, Safety Officer, Supervisor |
| GET | `/api/v1/risk/predictions` | Admin, Safety Officer, Supervisor, Compliance Officer, Viewer |
| POST | `/api/v1/chat/documents` | Admin, Safety Officer, Compliance Officer |
| POST | `/api/v1/chat/query` | Admin, Safety Officer, Supervisor, Compliance Officer, Viewer; rate limited |
| POST | `/api/v1/chat/incidents/{incident_id}/explain` | Admin, Safety Officer, Supervisor, Compliance Officer; rate limited |
| POST | `/api/v1/map/layouts` | Admin, Safety Officer |
| GET | `/api/v1/map/layouts/{plant_id}` | Admin, Safety Officer, Supervisor, Compliance Officer, Viewer |
| POST | `/api/v1/map/hazards` | Admin, Safety Officer |
| POST | `/api/v1/map/viewport` | Admin, Safety Officer, Supervisor, Compliance Officer, Viewer |
| GET | `/api/v1/map/alerts/{plant_id}` | Admin, Safety Officer, Supervisor, Compliance Officer, Viewer |
| GET | `/api/v1/timeline/incidents/{incident_id}` | Admin, Safety Officer, Supervisor, Compliance Officer |
| GET | `/api/v1/timeline/alerts/{alert_id}` | Admin, Safety Officer, Supervisor, Compliance Officer |
| GET | `/api/v1/incidents/{incident_id}/emergency-panel` | Admin, Safety Officer, Supervisor |
| GET | `/api/v1/incidents/{incident_id}/report` | Admin, Safety Officer, Supervisor, Compliance Officer |
| GET | `/api/v1/incidents/{incident_id}/report.csv` | Admin, Safety Officer, Compliance Officer |
| GET | `/api/v1/incidents/{incident_id}/report.pdf` | Admin, Safety Officer, Compliance Officer |
| GET | `/api/v1/incidents/reports/{report_type}` | Admin, Safety Officer, Compliance Officer |

## Residual Risk

The in-process rate limiter is acceptable for the current single-container demo. Production should replace the storage with Redis or another shared store so limits hold across multiple backend replicas. The Docker self-signed TLS certificate is for local/demo bootstrapping only; production must mount certificates from the deployment secret manager.
