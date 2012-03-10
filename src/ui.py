import urwid

class CursesUI:
    """
    A curses UI for the debugger.
    """
    def __init__(self):
        self.debugger = None
        self.currentMessage = ""
        self.messageBox = urwid.Text(self.currentMessage, wrap='clip')
        self.content = urwid.SimpleListWalker([])
        self.content_length = 0
        self.operations = {}
        self.focus = 0;

    def set_debugger(self, debugger):
        self.debugger = debugger # Maybe move to the constructor?

    def menu(self):
        menu = []
        for item in ["(O)pen file", "(E)xit", "<SPACE> Set breakpoint", "(R)un"]:
            menu.append(urwid.Text(item))
        return menu
    def print_message(self, message):
        self.currentMessage = message
        self.messageBox.set_text(self.currentMessage)

    def print_file(self, file_name, content, breakpoints = {}):
        del self.content[:]
        lines = content.split('\n')
        for line in lines:
            self.content.append(urwid.AttrMap(urwid.Text(line, wrap='clip'), None, 'reveal focus'))
        self.content_length = len(lines)

    def prompt(self):
        result = self.scr.getkey()
        if result == "o":
            self.print_message("Enter the path to the file to open")
        elif result == "x":
            self.print_message("yoyoyoyo")
            self.debugger.stop()

    def start(self):
        palette = [('header', 'white', 'black'),
                   ('reveal focus', 'black', 'dark cyan', 'standout'),]
        head = urwid.AttrMap(self.messageBox, 'header')
        columns = urwid.Columns(self.menu())
        self.listbox = urwid.ListBox(self.content)
        top = urwid.Frame(self.listbox, head, columns)
        self.loop = urwid.MainLoop(top, palette, unhandled_input=self.handle_input)
        self.loop.run()


    def handle_input(self, input):
        if input == 'enter':
            raise urwid.ExitMainLoop()
            self.stop()
        if input == 'down' and self.focus <= self.content_length:
            self.listbox.set_focus(self.focus)
            self.focus += 1
        if input == 'up' and self.content_length > 0:
            self.listbox.set_focus(self.focus)
            self.focus -= 1


    def stop(self):
        self.run = False

