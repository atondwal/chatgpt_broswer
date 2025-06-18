#!/usr/bin/env python3
"""
Modular ChatGPT conversation browser - Entry point.

This is the new modular version of cgpt.py that uses the extracted components.
The original cgpt.py is preserved for backward compatibility.

Usage:
    python cgpt_modular.py [command] [arguments]

Commands:
    list [count]                          - List conversations
    export <number> [--debug]             - Export specific conversation
    debug <number>                        - Debug conversation structure
    search <term> [--content] [--export]  - Search conversations
    info                                  - Show database information

Interactive mode (no arguments):
    Launches curses interface or falls back to simple terminal mode
"""

if __name__ == '__main__':
    from cli_parser import parse_and_execute
    parse_and_execute()