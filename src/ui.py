import curses

class CursesUI:
    """
    A curses UI for the debugger.
    """
    def __init__(self):
        self.scr = None
        self.debugger = None
        self.operations = {}
        self.run = True

    def start(self):
        self.scr = curses.initscr()
        #curses.cbreak()
        curses.halfdelay(20)
        curses.noecho()
        self.scr.keypad(1)

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

    def message_area(self, message):
        max = self.scr.getmaxyx()
        self.scr.hline(max[0]-2, 0, curses.ACS_HLINE, max[1])
        self.scr.addstr(max[0]-1, 0, message.strip())

    def print_message(self, message):
        self.message_area(message)

    def print_file(self, file_name, file, breakpoints = {}):
        self.message("Open: " + file_name)
        i = 3
        for line in file.split('\n'):
            self.scr.addstr(i, 0, line, curses.COLOR_GREEN)
            i += 1

    def tick(self):
        result = self.scr.getkey()

        if result == curses.ERR:
            return

        self.scr.clear() # not sure it's useful
        if result == "o":
            self.print_message("Enter the path to the file you wish to open")
        elif result == "x":
            self.debugger.stop()
        else:
            self.print_message(result)

        self.scr.refresh()

    def stop(self):
        self.run = False
        curses.nocbreak()
        self.scr.keypad(0)
        curses.echo()
        curses.endwin()

