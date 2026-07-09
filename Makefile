.PHONY: install init-db seed backend frontend

install:
	python3 -m venv .venv
	.venv/bin/pip install -r backend/requirements.txt
	cd frontend && npm install

init-db:
	cd backend && ../.venv/bin/python -m alembic upgrade head

seed:
	cd backend && ../.venv/bin/python -m scripts.seed_data

backend:
	cd backend && ../.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

frontend:
	cd frontend && npm run dev
