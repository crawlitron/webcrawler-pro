# =============================================================================
# WebCrawler Pro - Makefile
# =============================================================================

.PHONY: help up down build logs clean restart ps migrate shell-backend shell-frontend test lint

# Default target
.DEFAULT_GOAL := help

# Colors
GREEN  := \033[0;32m
YELLOW := \033[0;33m
BLUE   := \033[0;34m
RESET  := \033[0m

help: ## Show this help message
@echo ""
@echo "$(BLUE)WebCrawler Pro - Available Commands$(RESET)"
@echo "======================================"
@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
@echo ""

# =============================================================================
# Docker Compose Commands
# =============================================================================

up: ## Start all services in detached mode
@echo "$(GREEN)Starting WebCrawler Pro...$(RESET)"
docker compose up -d
@echo "$(GREEN)✅ Services started. App: http://localhost:80  (change APP_PORT in .env to use different port)$(RESET)"

down: ## Stop all services
@echo "$(YELLOW)Stopping WebCrawler Pro...$(RESET)"
docker compose down
@echo "$(YELLOW)✅ Services stopped$(RESET)"

build: ## Build and start all services
@echo "$(BLUE)Building and starting WebCrawler Pro...$(RESET)"
docker compose up --build -d
@echo "$(GREEN)✅ Build complete. Frontend: http://localhost:3000 | API: http://localhost:8000$(RESET)"

logs: ## Follow logs from all services
docker compose logs -f

logs-backend: ## Follow backend logs only
docker compose logs -f backend

logs-frontend: ## Follow frontend logs only
docker compose logs -f frontend

logs-worker: ## Follow celery worker logs only
docker compose logs -f worker

clean: ## Stop services and remove volumes (CAUTION: deletes all data!)
@echo "$(YELLOW)⚠️  WARNING: This will delete all data volumes!$(RESET)"
@read -p "Are you sure? [y/N] " CONFIRM && [ "$$CONFIRM" = "y" ] || exit 1
docker compose down -v
@echo "$(YELLOW)✅ Cleaned up all volumes$(RESET)"

restart: ## Restart all services
@echo "$(BLUE)Restarting WebCrawler Pro...$(RESET)"
docker compose restart
@echo "$(GREEN)✅ Services restarted$(RESET)"

ps: ## Show status of all services
docker compose ps

# =============================================================================
# Development Commands
# =============================================================================

shell-backend: ## Open shell in backend container
docker compose exec backend bash

shell-frontend: ## Open shell in frontend container
docker compose exec frontend sh

shell-db: ## Open psql in postgres container
docker compose exec postgres psql -U webcrawler -d webcrawler

migrate: ## Run database migrations (Alembic)
docker compose exec backend alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create MSG="your message")
docker compose exec backend alembic revision --autogenerate -m "$(MSG)"

# =============================================================================
# Testing & Linting
# =============================================================================

test: ## Run backend tests
docker compose exec backend pytest -v

lint: ## Run linting (flake8 + mypy)
docker compose exec backend flake8 app/ --max-line-length=100

format: ## Format code with black
docker compose exec backend black app/

# =============================================================================
# Production Commands
# =============================================================================

prod-up: ## Start production stack
docker compose -f docker-compose.prod.yml up -d

prod-down: ## Stop production stack
docker compose -f docker-compose.prod.yml down

prod-logs: ## Follow production logs
docker compose -f docker-compose.prod.yml logs -f

# =============================================================================
# Setup
# =============================================================================

setup: ## Initial project setup (copy .env.example)
@if [ ! -f .env ]; then \
cp .env.example .env; \
echo "$(GREEN)✅ .env file created from .env.example - Please edit it!$(RESET)"; \
else \
echo "$(YELLOW)⚠️  .env already exists, skipping$(RESET)"; \
fi
