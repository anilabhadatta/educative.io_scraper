.PHONY: help install run create clean

# Default Python command (use python3 on Unix-like systems)
PYTHON := python3

# Detect OS and adjust Python command if needed
ifeq ($(OS),Windows_NT)
	PYTHON := python
endif

help: ## Show this help message
	@echo "Available commands:"
	@echo "  make install  - Create virtual environment and install dependencies"
	@echo "  make run      - Run the Educative scraper"
	@echo "  make create   - Create an executable file of the scraper"
	@echo "  make clean    - Remove virtual environment and clean up"
	@echo ""
	@echo "Usage:"
	@echo "  make install && make run"

install: ## Create virtual environment and install dependencies
	$(PYTHON) setup.py --install

run: ## Run the Educative scraper
	$(PYTHON) setup.py --run

create: ## Create an executable file of the scraper
	$(PYTHON) setup.py --create

clean: ## Remove virtual environment and clean up
	@echo "Cleaning up virtual environment..."
	@rm -rf env
	@rm -rf __pycache__
	@rm -rf .pytest_cache
	@find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleanup complete!"

