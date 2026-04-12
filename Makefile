.PHONY: install run dev test lint format clean auth build publish

install:
	@echo "Installing dependencies..."
	pip install -e ".[dev]"
	@echo "Installation complete. You can run the bot with 'pdagent' or 'make run'."

run:
	pdagent

dev: install
	pdagent

setup: install
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env from example. Please edit it with your tokens."; \
	fi
	@python scripts/manage_auth.py

test:
	pytest -v

lint:
	flake8 pocket_desk_agent/
	mypy pocket_desk_agent/

format:
	black pocket_desk_agent/ scripts/

auth:
	python scripts/manage_auth.py

build:
	python -m build

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov dist build *.egg-info
