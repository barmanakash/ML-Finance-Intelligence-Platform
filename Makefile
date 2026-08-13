.PHONY: help install dev test test-ml lint format type-check db-init seed generate-data train evaluate mlflow docker-up docker-down docker-logs clean

help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install backend dependencies
	cd backend && pip install -r requirements-dev.txt

dev: ## Run backend in development mode
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test: ## Run tests
	cd backend && pytest tests/ -v --cov=app --cov-report=term-missing

test-ml: ## Run ML package tests (requires ml/requirements.txt + pytest installed)
	pytest ml/tests/ -v

lint: ## Run linter
	cd backend && ruff check .

format: ## Format code
	cd backend && ruff format .

type-check: ## Run type checker
	cd backend && mypy app/

db-init: ## Initialize database indexes
	python scripts/create_indexes.py

seed: ## Seed demo data
	python scripts/seed.py

generate-data: ## Generate the synthetic categorization training dataset
	python -m ml.datasets.generate_categorization_dataset

train: ## Train ML models
	python -m ml.categorization.train

evaluate: ## Evaluate the active ML model
	python -m ml.categorization.evaluate

mlflow: ## Open MLflow UI
	mlflow ui --port 5000

docker-up: ## Start all services with Docker
	docker compose up --build -d

docker-down: ## Stop all services
	docker compose down

docker-logs: ## View logs
	docker compose logs -f

clean: ## Clean build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf backend/.pytest_cache backend/.mypy_cache backend/.ruff_cache backend/htmlcov
