# loki-cli — developer Makefile
#
# Common workflows:
#   make install       - editable install with dev+build+docs extras
#   make lint          - run ruff
#   make fmt           - apply ruff auto-fixes + formatter
#   make test          - run pytest
#   make build-binary  - PyInstaller single-file binary in dist/
#   make docs          - preview MkDocs site locally on http://127.0.0.1:8000
#   make docs-build    - strict MkDocs build into site/
#   make docker        - build the loki-cli Docker image
#   make clean         - remove build/test/cache artifacts

PYTHON ?= python3
VENV   ?= .venv
BIN    := $(VENV)/bin
PIP    := $(BIN)/pip
LOKI   := $(BIN)/loki-cli

IMAGE ?= loki-cli:local

.PHONY: help install lint fmt test cov build-binary docs docs-build docker clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) 2>/dev/null | awk 'BEGIN{FS=":.*?## "}{printf "  %-14s %s\n", $$1, $$2}' || \
	 sed -n 's/^## //p' $(MAKEFILE_LIST)

$(VENV):
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip

install: $(VENV) ## Editable install with dev+build+docs extras
	$(PIP) install -e ".[dev,build,docs]"

lint: ## Run ruff checks
	$(BIN)/ruff check .

fmt: ## Apply ruff auto-fixes and formatting
	$(BIN)/ruff check --fix .
	$(BIN)/ruff format .

test: ## Run pytest
	$(BIN)/pytest

cov: ## Run pytest with coverage
	$(BIN)/pytest --cov=loki_cli --cov-report=term-missing

build-binary: ## Build a PyInstaller single-file executable
	$(BIN)/pyinstaller --clean --noconfirm loki-cli.spec
	@echo
	@echo "Built: $$(ls -lh dist/loki-cli* | awk '{print $$NF, $$5}')"

docs: ## Preview the MkDocs site locally
	$(BIN)/mkdocs serve

docs-build: ## Strict MkDocs build to ./site
	$(BIN)/mkdocs build --strict

docker: ## Build the loki-cli Docker image
	docker build -t $(IMAGE) .

clean: ## Remove build/test/cache artifacts
	rm -rf build/ dist/ site/ .pytest_cache/ .ruff_cache/ .coverage htmlcov/
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name '*.egg-info' -prune -exec rm -rf {} +
