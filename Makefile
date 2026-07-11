.PHONY: install init-db seed backend frontend build test quality docker-up docker-prod smoke backup-db backup-storage

install:
	python3 -m venv .venv
	.venv/bin/pip install -r backend/requirements.txt
	cd frontend && pnpm install

init-db:
	.venv/bin/python scripts/migrate.py

seed:
	.venv/bin/python scripts/seed.py

backend:
	cd backend && ../.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

frontend:
	cd frontend && pnpm dev

build:
	cd frontend && pnpm build

test:
	PYTHONPATH=backend .venv/bin/python -m unittest discover backend/tests

quality:
	PYTHONPYCACHEPREFIX=.pycache python3 -m compileall backend/app backend/scripts scripts
	PYTHONPATH=backend .venv/bin/python -m unittest discover backend/tests
	cd frontend && pnpm lint
	cd frontend && pnpm build

docker-up:
	docker compose up --build

docker-prod:
	docker compose -f docker-compose.prod.yml up -d --build

smoke:
	.venv/bin/python scripts/smoke_test.py

backup-db:
	scripts/backup/postgres_backup.sh

backup-storage:
	scripts/backup/storage_backup.sh
