import os
import json
import curses

HISTORY_PATH = os.path.expanduser('~/.chatgpt/history.json')  # adjust as needed

class HistoryOrganizer:
    def __init__(self, stdscr, history):
        self.stdscr = stdscr
        self.history = history  # list of {"id":..., "title":..., "messages":[...]}
        self.current = 0
        self.mode = 'list'  # or 'view'

    def run(self):
        curses.curs_set(0)
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
        for idx, convo in enumerate(self.history):
            prefix = '▶ ' if idx == self.current else '  '
            title = convo.get('title', f'Conversation {convo["id"]}')
            line = prefix + title
            if len(line) > w - 1:
                line = line[:w-4] + '...'
            self.stdscr.addstr(idx, 0, line)
        self.stdscr.addstr(h-1, 0, "Arrows: navigate · Enter: open · q: quit")

    def draw_view(self):
        h, w = self.stdscr.getmaxyx()
        convo = self.history[self.current]
        msgs = convo.get('messages', [])
        for idx, msg in enumerate(msgs[-(h-2):]):
            role = msg.get('role', 'user')
            text = msg.get('content', '')
            line = f"{role}: {text}"
            if len(line) > w - 1:
                line = line[:w-4] + '...'
            self.stdscr.addstr(idx, 0, line)
        self.stdscr.addstr(h-1, 0, "b: back · q: quit view")

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
            # expecting list of conversations
            return data.get('conversations', data)
    except Exception as e:
        return []

def main(stdscr):
    history = load_history(HISTORY_PATH)
    app = HistoryOrganizer(stdscr, history)
    app.run()

if __name__ == '__main__':
    curses.wrapper(main)
