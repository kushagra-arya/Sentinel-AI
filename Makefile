COMPOSE=docker compose --env-file .env -f infra/docker-compose.yml

.PHONY: up down migrate seed bootstrap reset-demo test ps logs

up:
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f --tail=200

migrate:
	$(COMPOSE) run --rm backend alembic upgrade head

seed:
	$(COMPOSE) run --rm backend python -m app.seed

bootstrap: up migrate seed

reset-demo: migrate seed

test:
	$(COMPOSE) run --rm backend pytest
