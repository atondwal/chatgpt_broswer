#!/usr/bin/env python3
"""
Quick test to see if TUI launches and the tree view works.
This script will launch the TUI for a few seconds then exit.
"""

import time
import signal
from chatgpt_tui import ChatGPTTUI

def signal_handler(signum, frame):
    print("\n⏰ Auto-exit after test")
    exit(0)

def main():
    print("🚀 Launching TUI for 5 seconds...")
    print("💡 Try pressing 't' to switch to tree view!")
    print("💡 Try pressing 'l' to switch back to list view!")
    print("💡 Try pressing 'q' to quit early!")
    
    # Set up auto-exit after 10 seconds
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(10)
    
    try:
        tui = ChatGPTTUI(debug=True)
        tui.run()
    except KeyboardInterrupt:
        print("\n👋 Manual exit")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()