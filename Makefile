# Makefile for ChatGPT Tree Organization

.PHONY: test test-unit test-integration test-edge test-cli test-all clean help

# Default target
help:
	@echo "ChatGPT Tree Organization - Test Commands"
	@echo "=========================================="
	@echo ""
	@echo "make test           - Run all tests (recommended)"
	@echo "make test-unit      - Run unit tests only"
	@echo "make test-integration - Run integration tests"
	@echo "make test-edge      - Run edge case tests"
	@echo "make test-cli       - Run CLI tests"
	@echo "make test-pytest    - Run tests with pytest"
	@echo "make clean          - Clean cache and temp files"
	@echo ""
	@echo "Individual test files:"
	@echo "  python test_conversation_tree.py"
	@echo "  python test_edge_cases.py"
	@echo "  python test_cli_integration.py"
	@echo "  python test_tui_launch.py"

# Run all tests
test:
	@echo "🚀 Running complete test suite..."
	@python test_all.py

# Run unit tests only
test-unit:
	@echo "🧪 Running unit tests..."
	@python test_conversation_tree.py

# Run integration tests
test-integration:
	@echo "🔗 Running integration tests..."
	@python test_cli_integration.py
	@python test_tui_launch.py

# Run edge case tests
test-edge:
	@echo "🔬 Running edge case tests..."
	@python test_edge_cases.py

# Run CLI tests
test-cli:
	@echo "⌨️  Running CLI tests..."
	@python test_cli_integration.py

# Run with pytest (if available)
test-pytest:
	@echo "🧪 Running tests with pytest..."
	@pytest test_conversation_tree.py -v --tb=short
	@pytest test_all.py::run_integration_tests -v --tb=short

# Clean cache and temporary files
clean:
	@echo "🧹 Cleaning cache and temporary files..."
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@find . -name "*.pyo" -delete 2>/dev/null || true
	@find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.tmp" -delete 2>/dev/null || true
	@find . -name "*.temp" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete"

# Quick syntax check
check:
	@echo "🔍 Checking syntax..."
	@python -m py_compile conversation_tree.py
	@python -m py_compile chatgpt_tui.py
	@python -m py_compile tree_constants.py
	@python -m py_compile tree_types.py
	@echo "✅ Syntax check passed"

# Run demo
demo:
	@echo "🎭 Running tree organization demo..."
	@python demo_tree_organization.py

# Show test coverage (if available)
coverage:
	@echo "📊 Running tests with coverage..."
	@python -m pytest test_conversation_tree.py --cov=conversation_tree --cov-report=term-missing || echo "Install pytest-cov for coverage: pip install pytest-cov"