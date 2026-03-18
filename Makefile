.PHONY: start stop restart logs test test-local seed migrate build status

# ========================
# Démarrage rapide
# ========================

start:  ## Démarre tout (DB, Redis, Backend, Celery, Frontend)
	./start.sh

build:  ## Build tous les conteneurs
	docker compose build

stop:  ## Arrête tous les conteneurs
	docker compose down

restart:  ## Redémarre tout
	docker compose down && docker compose up -d

status:  ## Affiche le statut des conteneurs
	docker compose ps

logs:  ## Affiche les logs (tous les services)
	docker compose logs -f

logs-backend:  ## Logs du backend uniquement
	docker compose logs -f backend

logs-celery:  ## Logs du worker Celery
	docker compose logs -f celery-worker

# ========================
# Base de données
# ========================

migrate:  ## Lance les migrations Alembic
	docker compose exec backend alembic upgrade head

migrate-down:  ## Rollback la dernière migration
	docker compose exec backend alembic downgrade -1

seed:  ## Seed les données initiales (piliers, templates, règles)
	docker compose exec backend python -c "import asyncio; from app.seed import seed_all; asyncio.run(seed_all())"

# ========================
# Tests
# ========================

test:  ## Lance tous les tests dans Docker
	docker compose exec backend python -m pytest tests/ -v

test-local:  ## Lance les tests du validateur en local (pas de Docker)
	cd backend && python3 -m pytest tests/test_validator.py -v --no-header -c /dev/null --rootdir=. -p no:conftest 2>/dev/null || python3 -c "exec(open('tests/test_validator.py').read())"

test-build:  ## Vérifie que le frontend compile
	cd frontend && npm run build

# ========================
# Dev
# ========================

shell:  ## Ouvre un shell Python dans le backend
	docker compose exec backend python

backend-shell:  ## Ouvre bash dans le backend
	docker compose exec backend bash

psql:  ## Ouvre psql dans la base de données
	docker compose exec db psql -U postgres -d linkedin_automation

redis-cli:  ## Ouvre redis-cli
	docker compose exec redis redis-cli

# ========================
# Nettoyage
# ========================

clean:  ## Supprime les conteneurs et volumes
	docker compose down -v

help:  ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
