PYTHON ?= python3
VENV ?= .venv
BIN := $(VENV)/bin
PIP := $(BIN)/pip
PYTEST := $(BIN)/pytest
UVICORN := $(BIN)/uvicorn

.PHONY: help venv install install-whatsapp run run-dev test review-format clean

help:
	@echo "Available targets:"
	@echo "  make venv             Create the local virtual environment"
	@echo "  make install          Install Python dependencies"
	@echo "  make install-whatsapp Install Node runtime dependencies for WhatsApp automation"
	@echo "  make run              Run the FastAPI service"
	@echo "  make run-dev          Run the FastAPI service with autoreload"
	@echo "  make test             Run Python tests"
	@echo "  make clean            Remove caches"

venv:
	$(PYTHON) -m venv $(VENV)

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install pytest

install-whatsapp:
	cd runtime && npm install && npx playwright install chromium

run:
	$(UVICORN) app.main:app --host 0.0.0.0 --port 8000

run-dev:
	$(UVICORN) app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	$(PYTEST) arabic_post_generator/tests

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
