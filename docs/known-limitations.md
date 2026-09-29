# Known Limitations

This repository is a demo/pilot implementation. It is intentionally broader than a scaffold, but several areas remain prototype-grade.

## Production-Grade Today

- Clean separation between route handlers, services, models, schemas, ML/rule modules, and RAG modules.
- PostgreSQL-backed evidence chains for alerts and incidents.
- Alembic migrations for schema evolution.
- JWT auth with refresh rotation and RBAC dependencies.
- Structured backend logging.
- Nginx reverse proxy and TLS termination.
- Deterministic synthetic dataset and replay controller.
- Demo-scale dashboard aggregation and performance check endpoint.
- Incident timeline and report generation from stored evidence links.

## Prototype-Grade Or Demo-Grade

- Rate limiting is process-local. Multi-instance deployments need Redis or another shared limiter backend.
- Nginx demo TLS uses an auto-generated self-signed certificate unless a real certificate is mounted.
- Sensor readings are indexed but not partitioned. Long-retention or sub-second production loads need partitioning, TimescaleDB, or a dedicated time-series strategy.
- ML models are bootstrap models trained on synthetic data, not validated on plant historical data.
- RAG embeddings are deterministic/local for demo behavior. Production should use an approved embedding model, corpus governance, and retrieval evaluation.
- ChromaDB persistence is local Docker volume based. Production should define backup/restore and retention procedures.
- Email notification is queued/audited but not integrated with a real SMTP or transactional email provider.
- SMS, Teams, and Slack channels are stubs behind a common interface.
- Frontend role scoping is mostly presentational. Backend route RBAC is enforced, but fine-grained area-level authorization needs dedicated data constraints.
- The incident history UI currently uses representative client-side records rather than a full backend incident-search endpoint.
- The demo replay controller is public for demo convenience. A pilot environment should protect or disable it outside controlled demo use.
- `npm audit` still reports advisories in the current Next.js dependency line that npm resolves only by moving to a Next 16-era framework stack. See `docs/demo-success-report.md`.

## Future Enhancements From Section 16

### Wearables

Would require:

- Worker wearable ingestion protocol and device identity model.
- Battery/device-health monitoring.
- Location confidence and stale-signal handling.
- Privacy and retention policy for worker telemetry.
- Rule-engine conditions for biometric and proximity data.

### Drone Inspection

Would require:

- Drone mission/event models.
- Media/object-detection pipeline.
- Geospatial alignment between drone findings and plant coordinates.
- Operator review workflow for CV findings.
- Evidence links from detected anomalies to alerts/incidents.

### Predictive Maintenance

Would require:

- Historical equipment failure labels.
- Feature store for equipment telemetry and work history.
- Model training/evaluation pipeline per asset class.
- Maintenance recommendation APIs.
- Integration with CMMS/work-order systems.

### Digital Twin

Would require:

- Canonical plant topology model.
- Equipment/process relationships beyond current zone labels.
- Real-time state synchronization with SCADA/IoT sources.
- Simulation engine for what-if risk propagation.
- Visualization primitives beyond the current 2D map.

### Voice Assistant

Would require:

- Speech-to-text and text-to-speech integration.
- Push-to-talk or wake-word UX suitable for control rooms.
- Strict confirmation flows for any mutating action.
- Full transcript audit logging.
- Noise/environment validation for plant conditions.

### Edge AI

Would require:

- Edge deployment packaging.
- Offline inference and sync queue.
- Model/version rollout strategy.
- Hardware acceleration and watchdog monitoring.
- Clear fail-safe behavior when edge/backend disagree.

### Federated Learning

Would require:

- Multi-site model governance.
- Secure aggregation protocol.
- Privacy threat model and data minimization.
- Per-plant model drift monitoring.
- Regulatory review for cross-site learned parameters.

### Multi-Plant Analytics

Would require:

- Tenant/plant hierarchy and authorization model.
- Cross-plant aggregation schemas.
- Regional dashboards and benchmarking.
- Data normalization across heterogeneous plant taxonomies.
- Stronger query performance strategy for fleet-wide analytics.
