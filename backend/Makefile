.PHONY: install dev test lint format

install:
	uv sync --all-extras

dev:
	PYTHONPATH=. uv run uvicorn src.main:app --reload --port 8001

test:
	PYTHONPATH=. uv run pytest -v

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/
