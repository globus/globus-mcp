.PHONY: help
help:
	@echo "Available targets:"
	@echo "  sync         - Install dependencies"
	@echo "  format       - Format and fix code"
	@echo "  format-check - Check code formatting"
	@echo "  lint         - Run linter"
	@echo "  mypy         - Run type checker"
	@echo "  test         - Run tests"
	@echo "  coverage     - Run tests with coverage report (95% required)"
	@echo "  check        - Run all checks (format-check, lint, mypy, test)"

.PHONY: sync
sync:
	uv sync --all-extras --all-packages --group dev

.PHONY: format
format: 
	uv run ruff format
	uv run ruff check --fix

.PHONY: format-check
format-check:
	uv run ruff format --check

.PHONY: lint
lint: 
	uv run ruff check

.PHONY: mypy
mypy: 
	uv run mypy .

.PHONY: test
test: 
	uv run pytest 

.PHONY: coverage
coverage:
	uv run coverage run -m pytest
	uv run coverage report -m --fail-under=95

.PHONY: check
check: format-check lint mypy test