# API Documentation Audit

Date: 2026-07-08

FastAPI serves OpenAPI at `/api/v1/openapi.json` and Swagger UI at `/api/v1/docs`; through Nginx these are available at `/api/openapi.json` and `/api/docs`.

Audit result: **Pass**. All application routes declare summaries, meaningful descriptions, response models where applicable, and `x-roles` OpenAPI metadata.

## Route Inventory

| Method | Route | Summary | Access metadata |
| --- | --- | --- | --- |
| POST | `/api/v1/auth/login` | Authenticate a user | `public` |
| POST | `/api/v1/auth/refresh` | Refresh an authenticated session | `public` |
| POST | `/api/v1/auth/logout` | Logout an authenticated user | `authenticated` |
| POST | `/api/v1/chat/documents` | Ingest a safety document | Admin, Safety Officer, Compliance Officer |
| POST | `/api/v1/chat/query` | Ask the AI Safety Assistant | Admin, Safety Officer, Supervisor, Compliance Officer, Viewer |
| POST | `/api/v1/chat/incidents/{incident_id}/explain` | Explain an incident from evidence and citations | Admin, Safety Officer, Supervisor, Compliance Officer |
| GET | `/api/v1/dashboard/summary` | Get command-center dashboard summary | Admin, Safety Officer, Supervisor, Compliance Officer, Viewer |
| POST | `/api/v1/demo/replay/start` | Start deterministic demo replay | `public` |
| POST | `/api/v1/demo/replay/advance` | Advance deterministic demo replay | `public` |
| GET | `/api/v1/demo/replay/status` | Get deterministic demo replay status | `public` |
| GET | `/api/v1/demo/performance/dashboard` | Measure dashboard performance | `public` |
| GET | `/api/v1/health` | Check backend liveness | `public` |
| GET | `/api/v1/health/ready` | Check backend readiness | `public` |
| GET | `/api/v1/incidents/{incident_id}/emergency-panel` | Get emergency response panel state | Admin, Safety Officer, Supervisor |
| GET | `/api/v1/incidents/{incident_id}/report` | Generate incident report | Admin, Safety Officer, Supervisor, Compliance Officer |
| GET | `/api/v1/incidents/{incident_id}/report.csv` | Export incident report as CSV | Admin, Safety Officer, Compliance Officer |
| GET | `/api/v1/incidents/{incident_id}/report.pdf` | Export incident report as PDF | Admin, Safety Officer, Compliance Officer |
| GET | `/api/v1/incidents/reports/{report_type}` | Get future report export status | Admin, Safety Officer, Compliance Officer |
| POST | `/api/v1/map/layouts` | Create plant layout | Admin, Safety Officer |
| GET | `/api/v1/map/layouts/{plant_id}` | Get active plant layout | Admin, Safety Officer, Supervisor, Compliance Officer, Viewer |
| POST | `/api/v1/map/hazards` | Create hazard zone | Admin, Safety Officer |
| POST | `/api/v1/map/viewport` | Get dynamic map viewport layers | Admin, Safety Officer, Supervisor, Compliance Officer, Viewer |
| GET | `/api/v1/map/alerts/{plant_id}` | Get evidence-positioned alert markers | Admin, Safety Officer, Supervisor, Compliance Officer, Viewer |
| POST | `/api/v1/notifications` | Dispatch a notification | Admin, Safety Officer, Supervisor |
| GET | `/api/v1/notifications` | List current-user notifications | Admin, Safety Officer, Supervisor, Compliance Officer, Viewer |
| POST | `/api/v1/notifications/{notification_id}/read` | Mark a notification as read | Admin, Safety Officer, Supervisor, Compliance Officer, Viewer |
| POST | `/api/v1/risk/rules/evaluate` | Evaluate compound risk rules | Admin, Safety Officer, Supervisor |
| POST | `/api/v1/risk/classify` | Classify current plant risk | Admin, Safety Officer, Supervisor |
| GET | `/api/v1/risk/predictions` | Predict telemetry risk trends | Admin, Safety Officer, Supervisor, Compliance Officer, Viewer |
| GET | `/api/v1/timeline/incidents/{incident_id}` | Reconstruct incident timeline | Admin, Safety Officer, Supervisor, Compliance Officer |
| GET | `/api/v1/timeline/alerts/{alert_id}` | Reconstruct alert timeline | Admin, Safety Officer, Supervisor, Compliance Officer |

## Notes

The demo controller endpoints are marked public for unattended demo automation. For pilot or production use, protect them behind Admin-only access or disable the router.
