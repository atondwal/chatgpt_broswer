#!/bin/bash
# Test runner script for ChatGPT Tree Organization
# Alternative to Makefile for environments without make

set -e

show_help() {
    echo "ChatGPT Tree Organization - Test Commands"
    echo "=========================================="
    echo ""
    echo "./run_tests.sh [command]"
    echo ""
    echo "Commands:"
    echo "  test            - Run all tests (recommended)"
    echo "  test-unit       - Run unit tests only"
    echo "  test-integration - Run integration tests"
    echo "  test-edge       - Run edge case tests"
    echo "  test-cli        - Run CLI tests"
    echo "  test-pytest     - Run tests with pytest"
    echo "  clean           - Clean cache and temp files"
    echo "  check           - Quick syntax check"
    echo "  demo            - Run tree organization demo"
    echo "  coverage        - Run tests with coverage"
    echo "  help            - Show this help"
    echo ""
    echo "Individual test files:"
    echo "  python test_conversation_tree.py"
    echo "  python test_edge_cases.py"
    echo "  python test_cli_integration.py"
    echo "  python test_tui_launch.py"
}

run_all_tests() {
    echo "🚀 Running complete test suite..."
    python test_all.py
}

run_unit_tests() {
    echo "🧪 Running unit tests..."
    python test_conversation_tree.py
}

run_integration_tests() {
    echo "🔗 Running integration tests..."
    python test_cli_integration.py
    python test_tui_launch.py
}

run_edge_tests() {
    echo "🔬 Running edge case tests..."
    python test_edge_cases.py
}

run_cli_tests() {
    echo "⌨️  Running CLI tests..."
    python test_cli_integration.py
}

run_pytest() {
    echo "🧪 Running tests with pytest..."
    pytest test_conversation_tree.py -v --tb=short
    pytest test_all.py::run_integration_tests -v --tb=short
}

clean_cache() {
    echo "🧹 Cleaning cache and temporary files..."
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "*.pyo" -delete 2>/dev/null || true
    find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.tmp" -delete 2>/dev/null || true
    find . -name "*.temp" -delete 2>/dev/null || true
    echo "✅ Cleanup complete"
}

check_syntax() {
    echo "🔍 Checking syntax..."
    python -m py_compile conversation_tree.py
    python -m py_compile chatgpt_tui.py
    python -m py_compile tree_constants.py
    python -m py_compile tree_types.py
    echo "✅ Syntax check passed"
}

run_demo() {
    echo "🎭 Running tree organization demo..."
    python demo_tree_organization.py
}

run_coverage() {
    echo "📊 Running tests with coverage..."
    python -m pytest test_conversation_tree.py --cov=conversation_tree --cov-report=term-missing || echo "Install pytest-cov for coverage: pip install pytest-cov"
}

# Main command processing
case "${1:-help}" in
    "test")
        run_all_tests
        ;;
    "test-unit")
        run_unit_tests
        ;;
    "test-integration")
        run_integration_tests
        ;;
    "test-edge")
        run_edge_tests
        ;;
    "test-cli")
        run_cli_tests
        ;;
    "test-pytest")
        run_pytest
        ;;
    "clean")
        clean_cache
        ;;
    "check")
        check_syntax
        ;;
    "demo")
        run_demo
        ;;
    "coverage")
        run_coverage
        ;;
    "help"|"--help"|"-h")
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        echo "Use './run_tests.sh help' for available commands"
        exit 1
        ;;
esac