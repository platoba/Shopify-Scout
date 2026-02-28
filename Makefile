.PHONY: install test lint clean docker run

install:
	pip install -e ".[dev]"

test:
	pytest tests/ -v --tb=short

test-cov:
	pytest tests/ -v --cov=app --cov-report=term-missing

lint:
	ruff check app/ tests/

lint-fix:
	ruff check --fix app/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .ruff_cache htmlcov

docker:
	docker compose build

docker-up:
	docker compose up -d

docker-test:
	docker compose run --rm test

run:
	python bot.py

cli-analyze:
	python -m app.cli analyze $(DOMAIN)

cli-compare:
	python -m app.cli compare $(DOMAINS)
