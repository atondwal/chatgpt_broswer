import os
import json
import curses
import sys

# Change this to point to your actual conversations.json file
HISTORY_PATH = os.path.expanduser('~/.chatgpt/conversations.json')

class HistoryOrganizer:
    def __init__(self, stdscr, history):
        self.stdscr = stdscr
        self.history = history  # list of {"id":..., "title":..., "messages":[...]}
        self.current = 0
        self.mode = 'list'  # or 'view'

    def run(self):
        try:
            curses.curs_set(0)  # May fail in some terminals
        except:
            pass
        self.stdscr.keypad(True)
        while True:
            self.stdscr.clear()
            if self.mode == 'list':
                self.draw_list()
            else:
                self.draw_view()
            self.stdscr.refresh()
            key = self.stdscr.getch()
            if key in (ord('q'), 27):  # q or ESC
                break
            self.handle_input(key)

    def draw_list(self):
        h, w = self.stdscr.getmaxyx()
        for idx, convo in enumerate(self.history[:h-2]):  # Limit to screen height
            prefix = '▶ ' if idx == self.current else '  '
            title = convo.get('title', f'Conversation {convo.get("id", idx)}')
            line = prefix + title
            if len(line) > w - 1:
                line = line[:w-4] + '...'
            try:
                self.stdscr.addstr(idx, 0, line)
            except curses.error:
                # Skip if we hit screen boundaries
                pass
        try:
            self.stdscr.addstr(h-1, 0, "Arrows: navigate · Enter: open · q: quit")
        except curses.error:
            pass

    def draw_view(self):
        h, w = self.stdscr.getmaxyx()
        convo = self.history[self.current]
        msgs = convo.get('messages', [])
        for idx, msg in enumerate(msgs[-(h-2):]):  # Show last h-2 messages
            role = msg.get('role', 'user')
            text = msg.get('content', '')
            if isinstance(text, list):  # Handle content arrays
                text = " ".join([item.get('text', '') if isinstance(item, dict) else str(item) for item in text])
            line = f"{role}: {text}"
            if len(line) > w - 1:
                line = line[:w-4] + '...'
            try:
                self.stdscr.addstr(idx, 0, line)
            except curses.error:
                # Skip if we hit screen boundaries
                pass
        try:
            self.stdscr.addstr(h-1, 0, "b: back · q: quit view")
        except curses.error:
            pass

    def handle_input(self, key):
        if self.mode == 'list':
            if key == curses.KEY_UP and self.current > 0:
                self.current -= 1
            elif key == curses.KEY_DOWN and self.current < len(self.history) - 1:
                self.current += 1
            elif key in (curses.KEY_ENTER, 10, 13):
                self.mode = 'view'
        else:
            if key in (ord('b'),):
                self.mode = 'list'
            # optional scroll view

def load_history(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Check for expected format
            if isinstance(data, dict):
                return data.get('conversations', [])
            elif isinstance(data, list):
                return data
            else:
                print(f"Unexpected data format: {type(data)}")
                return []
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return []
    except Exception as e:
        print(f"Error loading history: {e}")
        return []

def simple_mode(path):
    """Alternative non-curses mode that just prints the conversations"""
    history = load_history(path)
    if not history:
        print("No conversations found.")
        return
    
    print(f"Found {len(history)} conversations")
    for i, convo in enumerate(history[:10]):  # Show first 10 conversations
        title = convo.get('title', f"Conversation {convo.get('id', i)}")
        print(f"{i+1}. {title}")
    
    print("\nUse the curses interface to browse all conversations.")

def main(stdscr):
    try:
        history = load_history(HISTORY_PATH)
        if not history:
            stdscr.addstr(0, 0, "No conversations found or error loading history.")
            stdscr.addstr(1, 0, f"Path checked: {HISTORY_PATH}")
            stdscr.addstr(2, 0, "Press any key to exit.")
            stdscr.refresh()
            stdscr.getch()
            return
        
        app = HistoryOrganizer(stdscr, history)
        app.run()
    except Exception as e:
        stdscr.clear()
        stdscr.addstr(0, 0, f"Error: {str(e)}")
        stdscr.addstr(1, 0, "Press any key to exit.")
        stdscr.refresh()
        stdscr.getch()

if __name__ == '__main__':
    # Try using curses, but fall back to simple mode if it fails
    try:
        curses.wrapper(main)
    except Exception as e:
        print(f"Error initializing curses: {e}")
        print("Falling back to simple mode...\n")
        simple_mode(HISTORY_PATH)
