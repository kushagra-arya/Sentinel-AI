# SentinelAI Deployment Runbook

This runbook deploys the SentinelAI demo/pilot stack on a single Docker host. It is production-shaped for a pilot environment: Nginx is the only public entrypoint, stateful data is persisted in named volumes, services have health checks, restart policies, and resource limits, and migrations/seeding are explicit operational steps.

## Services

| Service | Purpose | External exposure | Health check |
| --- | --- | --- | --- |
| `nginx` | TLS terminator and reverse proxy for frontend/backend | `${NGINX_PORT:-80}`, `${NGINX_TLS_PORT:-443}` | `GET http://localhost/health` |
| `frontend` | Next.js UI | Internal only, behind Nginx | `GET http://localhost:3000` inside container |
| `backend` | FastAPI API and demo controller | Internal only, behind Nginx | `GET http://localhost:8000/api/v1/health` inside container |
| `postgres` | Relational/time-series data | Internal only | `pg_isready` |
| `chromadb` | RAG vector store | Internal only | `GET /api/v1/heartbeat` inside container |

## Required Host Prerequisites

- Docker Engine with Compose v2.
- Git.
- Ports 80 and 443 available on the host, or custom `NGINX_PORT` / `NGINX_TLS_PORT`.
- At least 4 CPU cores and 8 GB RAM recommended for a smooth live demo.

## Required Secrets And Environment

Copy `.env.example` to `.env` and replace demo defaults before any pilot deployment.

Required secret values:

- `SECRET_KEY`: JWT signing secret. Use at least 32 random bytes encoded as hex or base64.
- `POSTGRES_PASSWORD`: database password. Use a generated secret, not the example value.

Required public/config values:

- `POSTGRES_USER`
- `POSTGRES_DB`
- `DATABASE_URL`
- `CHROMA_URL`
- `CHROMA_COLLECTION`
- `PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_API_BASE_URL`
- `NGINX_PORT`
- `NGINX_TLS_PORT`

No application secret is baked into the Docker images. Secrets are provided at runtime through `.env`, Compose environment expansion, or an external deployment secret manager.

## TLS

The Compose stack creates an ephemeral self-signed certificate in the `nginx_certs` named volume when no certificate exists. This is acceptable for local demos and dry runs.

For a pilot environment, replace the generated certificate with a real certificate:

1. Create or provision `tls.crt` and `tls.key`.
2. Mount them into `/etc/nginx/certs` for the `nginx` service.
3. Keep the filenames `tls.crt` and `tls.key`, or update `infra/nginx/default.conf`.

Nginx redirects HTTP to HTTPS except `/health`, which remains HTTP for simple load-balancer health checks.

## Fresh Machine Deployment

From a fresh machine:

```bash
git clone <repo-url> SentinelAi
cd SentinelAi
cp .env.example .env
```

Edit `.env` and replace at least:

```bash
SECRET_KEY=<generated-secret>
POSTGRES_PASSWORD=<generated-password>
DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
PUBLIC_API_BASE_URL=https://<demo-host>/api
NEXT_PUBLIC_API_BASE_URL=https://<demo-host>/api
```

Start, migrate, and seed:

```bash
make bootstrap
```

Equivalent explicit commands:

```bash
make up
make migrate
make seed
```

Check health:

```bash
make ps
curl -k https://localhost/health
curl -k https://localhost/api/health
curl -k https://localhost/api/health/ready
```

Open the UI:

```text
https://localhost
```

For the scripted live demo, start the replay controller:

```bash
curl -k -X POST https://localhost/api/demo/replay/start \
  -H "Content-Type: application/json" \
  -d '{"mode":"accelerated","speed_multiplier":600}'
```

Demo credentials are returned by the replay status endpoint and currently seed as:

- Email: `demo.admin@sentinelai.local`
- Password: `DemoPass123!`

## Reset Between Demos

To reset the demo data while preserving service volumes:

```bash
make reset-demo
```

Then restart the replay:

```bash
curl -k -X POST https://localhost/api/demo/replay/start \
  -H "Content-Type: application/json" \
  -d '{"mode":"accelerated","speed_multiplier":600}'
```

To reset all persisted state on a disposable demo host:

```bash
docker compose --env-file .env -f infra/docker-compose.yml down -v
make bootstrap
```

The `down -v` command deletes Postgres, ChromaDB, and generated Nginx certificate volumes. Do not run it on a pilot environment without an approved backup.

## Migrations And Seed

Migrations run through the backend image:

```bash
make migrate
```

Seed runs through the same image:

```bash
make seed
```

The seed command loads the deterministic synthetic demo dataset from `data/synthetic/generator.py` through `python -m app.seed`.

## Monitoring And Health

Basic operational checks:

```bash
make ps
make logs
curl -k https://localhost/health
curl -k https://localhost/api/health
curl -k https://localhost/api/health/ready
curl -k "https://localhost/api/demo/performance/dashboard?plant_id=<plant_id>"
```

Expected:

- Compose shows all services as healthy.
- `/health` returns backend liveness through Nginx.
- `/api/health/ready` confirms backend dependency readiness.
- Dashboard performance endpoint reports `passed: true` below the 2000 ms budget.

For deeper troubleshooting:

```bash
docker compose --env-file .env -f infra/docker-compose.yml logs backend
docker compose --env-file .env -f infra/docker-compose.yml logs nginx
docker compose --env-file .env -f infra/docker-compose.yml logs postgres
docker compose --env-file .env -f infra/docker-compose.yml logs chromadb
```

## Rollback Procedure

Before upgrading:

1. Record the current Git commit or image tag.
2. Take a database backup.
3. Record the current Alembic revision:

```bash
docker compose --env-file .env -f infra/docker-compose.yml run --rm backend alembic current
```

Rollback application code:

```bash
git checkout <previous-known-good-commit>
make up
```

If the rollback crosses a database migration boundary, review the Alembic downgrade path first:

```bash
docker compose --env-file .env -f infra/docker-compose.yml run --rm backend alembic history
docker compose --env-file .env -f infra/docker-compose.yml run --rm backend alembic downgrade <target_revision>
```

If downgrade is unsafe or unavailable, restore the Postgres volume from backup and restart:

```bash
make up
make ps
```

Rollback validation:

```bash
curl -k https://localhost/api/health/ready
curl -k -X POST https://localhost/api/demo/replay/start \
  -H "Content-Type: application/json" \
  -d '{"mode":"accelerated","speed_multiplier":600}'
```

## Operational Notes

- Only Nginx publishes host ports. Backend, frontend, Postgres, and ChromaDB communicate over the `sentinelai` Docker network by service name.
- The Compose file uses named volumes: `postgres_data`, `chroma_data`, and `nginx_certs`.
- Services use `restart: unless-stopped`, health checks, CPU limits, memory limits, and PID limits for pilot stability.
- Structured backend logs go to container stdout/stderr and can be collected by the host logging driver.
