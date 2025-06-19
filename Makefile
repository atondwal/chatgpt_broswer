# Makefile for ChatGPT Browser

.PHONY: test clean help install run

# Default target
help:
	@echo "ChatGPT Browser - Available Commands"
	@echo "===================================="
	@echo ""
	@echo "make install    - Install the package in development mode"
	@echo "make test       - Run all tests"
	@echo "make clean      - Clean cache and temp files"
	@echo "make run        - Run the TUI browser"
	@echo ""

# Install in development mode
install:
	pip install -e .

# Run all tests
test:
	@echo "🧪 Running tests..."
	@pytest tests/ -v

# Run the TUI
run:
	@echo "🚀 Starting ChatGPT Browser..."
	@python scripts/cgpt-tui.py conversations.json

# Clean cache and temporary files
clean:
	@echo "🧹 Cleaning cache and temporary files..."
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@find . -name "*.pyo" -delete 2>/dev/null || true
	@find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.tmp" -delete 2>/dev/null || true
	@find . -name "*.temp" -delete 2>/dev/null || true
	@find . -name "*.bak" -delete 2>/dev/null || true
	@find . -name "*.backup" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete"