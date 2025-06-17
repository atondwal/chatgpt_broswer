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
    """Alternative non-curses mode that allows viewing conversations"""
    history = load_history(path)
    if not history:
        print("No conversations found.")
        return
    
    page_size = 20
    current_page = 0
    total_pages = (len(history) + page_size - 1) // page_size
    
    while True:
        # Clear screen
        print("\033[H\033[J", end="")
        
        start_idx = current_page * page_size
        end_idx = min(start_idx + page_size, len(history))
        
        print(f"Found {len(history)} conversations - Page {current_page + 1}/{total_pages}")
        print("=" * 50)
        
        for i, convo in enumerate(history[start_idx:end_idx]):
            display_idx = start_idx + i + 1
            title = convo.get('title', f"Conversation {convo.get('id', i)}")
            print(f"{display_idx}. {title}")
        
        print("\nOptions:")
        print("  Enter a number to view a conversation")
        print("  n - Next page")
        print("  p - Previous page")
        print("  s - Search conversations")
        print("  q - Quit")
        
        choice = input("\nEnter your choice: ").strip().lower()
        
        if choice == 'q':
            break
        elif choice == 'n' and current_page < total_pages - 1:
            current_page += 1
        elif choice == 'p' and current_page > 0:
            current_page -= 1
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(history):
                view_conversation(history[idx])
            else:
                print("Invalid conversation number")
                input("Press Enter to continue...")
        elif choice == 's':
            search_term = input("Enter search term: ").strip().lower()
            if not search_term:
                continue
                
            results = [c for c in history if search_term in c.get('title', '').lower()]
            
            if not results:
                print("No matching conversations found")
                input("Press Enter to continue...")
                continue
                
            # Sub-menu for search results
            search_page = 0
            search_pages = (len(results) + page_size - 1) // page_size
            
            while True:
                # Clear screen
                print("\033[H\033[J", end="")
                
                s_start = search_page * page_size
                s_end = min(s_start + page_size, len(results))
                
                print(f"Found {len(results)} matching conversations - Page {search_page + 1}/{search_pages}")
                print(f"Search term: '{search_term}'")
                print("=" * 50)
                
                for i, convo in enumerate(results[s_start:s_end]):
                    display_idx = i + 1
                    title = convo.get('title', f"Conversation {convo.get('id', i)}")
                    print(f"{display_idx}. {title}")
                
                print("\nOptions:")
                print("  Enter a number to view a conversation")
                print("  n - Next page")
                print("  p - Previous page")
                print("  b - Back to main menu")
                
                sub_choice = input("\nEnter your choice: ").strip().lower()
                
                if sub_choice == 'b':
                    break
                elif sub_choice == 'n' and search_page < search_pages - 1:
                    search_page += 1
                elif sub_choice == 'p' and search_page > 0:
                    search_page -= 1
                elif sub_choice.isdigit():
                    idx = int(sub_choice) - 1 + s_start
                    if 0 <= idx < len(results):
                        view_conversation(results[idx])
                    else:
                        print("Invalid conversation number")
                        input("Press Enter to continue...")

def view_conversation(convo):
    """Display a conversation in simple text mode"""
    try:
        # Clear screen
        print("\033[H\033[J", end="")
        
        title = convo.get('title', 'Untitled Conversation')
        print(f"Conversation: {title}")
        print("=" * 50)
        
        msgs = convo.get('messages', [])
        if not msgs:
            print("\nNo messages found in this conversation.")
        
        for i, msg in enumerate(msgs):
            try:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                
                # Handle content that might be a list (for newer ChatGPT formats)
                if isinstance(content, list):
                    content_parts = []
                    for part in content:
                        if isinstance(part, dict) and 'text' in part:
                            content_parts.append(part['text'])
                        elif isinstance(part, str):
                            content_parts.append(part)
                    content = ' '.join(content_parts)
                
                print(f"\n{role.upper()}:")
                print("-" * 50)
                print(content)
                
                # If there are many messages, offer pagination
                if i > 0 and i % 5 == 0 and i < len(msgs) - 1:
                    response = input("\nPress Enter to continue, 'q' to return to list: ")
                    if response.lower() == 'q':
                        break
                    # Clear screen for next set of messages
                    print("\033[H\033[J", end="")
                    print(f"Conversation: {title} (continued)")
                    print("=" * 50)
            except Exception as e:
                print(f"\nError displaying message {i+1}: {str(e)}")
                continue
        
        print("\n" + "=" * 50)
        input("Press Enter to return to the conversation list...")
    except Exception as e:
        print(f"\nError viewing conversation: {str(e)}")
        input("Press Enter to return to the conversation list...")

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

def export_conversation(history, idx=0):
    """Export a single conversation to stdout"""
    if not history or idx >= len(history):
        print("No conversation found at index", idx)
        return
    
    convo = history[idx]
    title = convo.get('title', 'Untitled Conversation')
    print(f"Conversation: {title}")
    print("=" * 50)
    
    msgs = convo.get('messages', [])
    if not msgs:
        print("\nNo messages found in this conversation.")
        return
    
    for i, msg in enumerate(msgs):
        try:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            
            # Handle content that might be a list (for newer ChatGPT formats)
            if isinstance(content, list):
                content_parts = []
                for part in content:
                    if isinstance(part, dict) and 'text' in part:
                        content_parts.append(part['text'])
                    elif isinstance(part, str):
                        content_parts.append(part)
                content = ' '.join(content_parts)
            
            print(f"\n{role.upper()}:")
            print("-" * 50)
            print(content)
        except Exception as e:
            print(f"\nError displaying message {i+1}: {str(e)}")

def list_conversations(history, count=20):
    """List available conversations"""
    print(f"Found {len(history)} conversations")
    print("=" * 50)
    for i, convo in enumerate(history[:count]):
        title = convo.get('title', f"Conversation {convo.get('id', i)}")
        print(f"{i+1}. {title}")

if __name__ == '__main__':
    import sys
    
    history = load_history(HISTORY_PATH)
    
    if len(sys.argv) > 1:
        # Command-line argument mode
        if sys.argv[1] == "list":
            # List conversations
            count = 20
            if len(sys.argv) > 2 and sys.argv[2].isdigit():
                count = int(sys.argv[2])
            list_conversations(history, count)
        elif sys.argv[1] == "export" and len(sys.argv) > 2:
            # Export a specific conversation
            try:
                idx = int(sys.argv[2]) - 1  # Convert to 0-based index
                export_conversation(history, idx)
            except ValueError:
                print("Error: Please provide a valid conversation number")
        elif sys.argv[1] == "search" and len(sys.argv) > 2:
            # Search for conversations
            term = sys.argv[2].lower()
            results = [c for c in history if term in c.get('title', '').lower()]
            if results:
                print(f"Found {len(results)} conversations matching '{term}':")
                for i, convo in enumerate(results[:20]):
                    print(f"{i+1}. {convo.get('title', f'Conversation {convo.get('id', i)}')}")
            else:
                print(f"No conversations found matching '{term}'")
        else:
            print("Usage:")
            print("  python cgpt.py list [count]       - List conversations")
            print("  python cgpt.py export <number>    - Export conversation by number")
            print("  python cgpt.py search <term>      - Search for conversations")
    else:
        # Try interactive mode if no arguments provided
        try:
            # First try curses interface
            curses.wrapper(main)
        except Exception as e:
            # Fall back to simple mode
            print(f"Error initializing curses: {e}")
            print("Falling back to simple mode...\n")
            try:
                simple_mode(HISTORY_PATH)
            except Exception as e:
                # If simple mode fails, show usage
                print(f"Error in simple mode: {e}")
                print("\nUsage:")
                print("  python cgpt.py list [count]       - List conversations")
                print("  python cgpt.py export <number>    - Export conversation by number")
                print("  python cgpt.py search <term>      - Search for conversations")
