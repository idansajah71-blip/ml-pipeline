.PHONY: help install dev seed test docker-up docker-down

help:
	@echo "ML Pipeline - Available Commands:"
	@echo "  make install     - Install dependencies"
	@echo "  make dev         - Run development server"
	@echo "  make seed        - Seed database with sample data"
	@echo "  make test        - Run tests"
	@echo "  make docker-up   - Start with Docker Compose"
	@echo "  make docker-down - Stop Docker Compose"

install:
	pip install -r requirements.txt

dev:
	python run.py

seed:
	python scripts/seed.py

test:
	pytest app/tests/ -v

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-build:
	docker-compose build --no-cache
