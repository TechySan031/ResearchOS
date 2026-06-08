# ==============================
# ResearchOS Makefile
# ==============================

.PHONY: help install dev backend frontend lint test clean docker-up docker-down

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ----- Setup -----
install: ## Install all dependencies
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

# ----- Development -----
dev: ## Run both backend and frontend in development mode
	@echo "Starting ResearchOS development servers..."
	$(MAKE) -j2 backend frontend

backend: ## Run FastAPI backend
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend: ## Run Next.js frontend
	cd frontend && npm run dev

# ----- Quality -----
lint: ## Run linters
	cd backend && ruff check app/ --fix
	cd backend && ruff format app/
	cd frontend && npm run lint

test: ## Run all tests
	cd backend && pytest tests/ -v --tb=short

test-unit: ## Run unit tests only
	cd backend && pytest tests/unit/ -v --tb=short

test-integration: ## Run integration tests only
	cd backend && pytest tests/integration/ -v --tb=short

# ----- Database -----
db-migrate: ## Create new migration
	cd backend && alembic revision --autogenerate -m "$(msg)"

db-upgrade: ## Apply migrations
	cd backend && alembic upgrade head

db-downgrade: ## Rollback last migration
	cd backend && alembic downgrade -1

# ----- Docker -----
docker-up: ## Start infrastructure services
	docker-compose up -d

docker-down: ## Stop infrastructure services
	docker-compose down

docker-build: ## Build application containers
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# ----- Cleanup -----
clean: ## Remove build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -rf backend/dist backend/build
	rm -rf frontend/.next frontend/out
