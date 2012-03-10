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
        self.operations = {}

    def set_debugger(self, debugger):
        self.debugger = debugger # Maybe move to the constructor?

    def menu(self):
        return ["(O)pen file", "(E)xit", "<SPACE> Set breakpoint", "(R)un"];

    def print_message(self, message):
        self.currentMessage = message
        self.messageBox.set_text(self.currentMessage)

    def print_file(self, file_name, content, breakpoints = {}):
        self.print_message(file_name)
        for line in content.split('\n'):
            self.content.append(urwid.Text(line, wrap='clip'))

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
        self.listbox = urwid.ListBox(self.content)
        top = urwid.Frame(self.listbox, head)
        self.loop = urwid.MainLoop(top, palette,
                              input_filter=self.show_all_input, unhandled_input=self.exit_on_cr)
        self.loop.run()

        
    def show_all_input(self, input, raw):
        self.print_message(self.currentMessage)
        #self.messageBox.set_text(u"Pressed: " + u" ".join([
        #unicode(i) for i in input]))
        return input

    def exit_on_cr(self, input):
        if input == 'enter':
            raise urwid.ExitMainLoop()
            self.stop()
        if input == 'down':
            self.listbox.set_focus(1)

    def stop(self):
        self.run = False

