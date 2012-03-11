import curses

class CursesUI:
    """
    A curses UI for the debugger.
    """
    def __init__(self):
        self.scr = curses.initscr()
        self.debugger = None
        self.operations = {}
        curses.cbreak()
        curses.noecho()
        self.scr.keypad(1)
        self.run = True

    def set_debugger(self, debugger):
        self.debugger = debugger # Maybe move to the constructor?

    def menu(self):
        return ["(O)pen file", "E(x)it", "<SPACE> Set breakpoint", "(R)un"];

    def header(self, message, show_menu = True):
        max = self.scr.getmaxyx()
        pos = 0
        self.scr.hline(0, 0, curses.ACS_HLINE, max[1])
        if show_menu:
            for item in self.menu():
                self.scr.addstr(1, pos, item)
                self.scr.addstr(1, pos + len(item) + 1, '|')
                pos += len(item) + 3;
        self.scr.addstr(1, max[1]-(len(message)+1), message)
        self.scr.hline(2, 0, curses.ACS_HLINE, max[1])

    def print_message(self, message):
        self.scr.clear()
        self.header(message, False)
        self.scr.refresh()

    def print_file(self, file_name, file, breakpoints = {}):
        self.scr.clear()
        self.header(file_name)
        i = 3
        for line in file.split('\n'):
            self.scr.addstr(i, 0, line, curses.COLOR_GREEN)
            i += 1
        self.scr.refresh()

    def prompt(self):
        result = self.scr.getkey()
        if result == "o":
            self.print_message("Enter the path to the file to open")
        elif result == "x":
            self.debugger.stop()

    def start(self):
        while self.run:
            self.prompt()

    def stop(self):
        self.run = False
        curses.nocbreak()
        self.scr.keypad(0)
        curses.echo()
        curses.endwin()
