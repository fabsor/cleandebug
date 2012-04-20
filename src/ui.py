import urwid
import debugger
from pprint import PrettyPrinter
from debugger import LineBreakPoint

class CursesUI:
    """
    A curses UI for the debugger.
    """
    def __init__(self, debugger):
        self.debugger = debugger
        self.currentMessage = ""
        self.messageBox = urwid.Text(self.currentMessage)
        self.content = urwid.SimpleListWalker([])
        self.context_view = ContextView(debugger)
        self.input = urwid.Edit()
        self.stateMachine = StateMachine(self)
        self.stateMachine.add_mode(OpenFileMode(self))
        self.stateMachine.add_mode(FileExplorerMode(self))
        self.stateMachine.add_mode(ExitMode(self))
        self.stateMachine.add_mode(RunMode(self))
        self.file_loaded = False
        self.focus = 0;
        self.loop = None

    def menu(self):
        menu = []
        for item in ["(O)pen file", "(E)xit", "<SPACE> Set breakpoint", "(R)un", "(V)ariables"]:
            menu.append(urwid.Text(item))
        return menu
    def print_message(self, message):
        self.currentMessage = message
        self.messageBox.set_text(self.currentMessage)

    def refresh(self):
        if self.loop:
            self.loop.draw_screen()

    def print_file(self, file_name, content, breakpoints = []):
        del self.content[:]
        lines = content.split('\n')
        for line in lines:
            text_line = SelectableText(line, self.content)
            self.content.append(urwid.AttrMap(text_line, None, 'reveal focus'))
        for breakpoint in breakpoints:
            self.content[breakpoint.line_number-1].set_attr_map({ None: 'streak' })
        self.file_loaded = True
        self.file_name = file_name

    def print_context(self, context_names, context):
        self.context_view.render_view(context_names, context)

    def trigger_breakpoint(self, line):
        line -= 1
        if line < len(self.content):
            self.content[line].set_attr_map({ None: 'triggered' })

    def start(self):
        palette = [('header', 'white', 'black'),
                   ('reveal focus', 'black', 'dark cyan', 'standout'),
                   ('streak', 'black', 'dark red', 'standout'),
                   ('triggered', 'black', 'dark green', 'standout')]
        head = urwid.AttrMap(self.messageBox, 'header')
        columns = urwid.Columns(self.menu())
        footer = urwid.Pile([columns, self.input])
        self.listbox = urwid.ListBox(self.content)
        self.frame = urwid.Frame(urwid.Columns([self.listbox, self.context_view]), head, footer)
        self.loop = urwid.MainLoop(self.frame, palette, unhandled_input=self.stateMachine.handle_input)
        self.stateMachine.evaluate_modes()
        self.debugger.start()
        self.loop.run()

    def stop(self):
        self.run = False

class SelectableText(urwid.Text):
    def __init__(self, value, listWalker):
        urwid.Text.__init__(self, value)
        self._selectable = True
        self.listWalker = listWalker

    def keypress(self, size, key):
        focus = self.listWalker.get_focus()[1]
        if key == "down" and len(self.listWalker) < focus:
            self.listWalker.set_focus(self.listWalker.get_next(focus)[1])
        if key == "up" and focus > 0:
            self.listWalker.set_focus(focus)
        return key

class ContextView(urwid.Frame):
    """
    This is a view for displaying the current debugger context.
    """
    def __init__(self, debugger):
        self.content = urwid.SimpleListWalker([])
        self.content_box = urwid.ListBox(self.content)
        self.menu = urwid.Columns([])
        self.debugger = debugger
        urwid.Frame.__init__(self, self.content_box, self.menu)

    def render_view(self, context_names, context):
        """
        Render the view with a set of context names and a context.
        """
        del self.content[:]
        for context_name in context_names:
            self.menu.widget_list.append(urwid.Button(context_name["name"], self.change_context, context_name["id"]))
        for name,attributes in context.iteritems():
            text_line = SelectableText(name, self.content)
            self.content.append(urwid.AttrMap(text_line, None, 'reveal focus'))

    def change_context(self, context_id):
        pass

class StateMachine:
    """
    This simple state machine keeps track of what mode we are currently in.
    """
    def __init__(self, ui):
        self.ui = ui
        self.modes = []
        self.current_mode = None

    def add_mode(self, mode):
        self.modes.append(mode)

    def remove_mode(self, mode):
        self.modes.remove(mode)

    def evaluate_modes(self, text=None):
        for mode in self.modes:
            if mode.evaluate(text):
                self.set_mode(mode)
                break

    def handle_input(self, text):
        if not self.current_mode or not self.current_mode.locked():
            self.evaluate_modes(text)
        if self.current_mode and hasattr(self.current_mode, "handle_input") and callable(getattr(self.current_mode, "handle_input")):
            self.current_mode.handle_input(text)

    def set_previous_mode(self):
        self.current_mode = self.previous_mode

    def set_mode(self, mode):
        self.previous_mode= self.current_mode
        self.current_mode = mode
        # If the class has a method called enter, go ahead and call it.
        if hasattr(mode, "enter") and callable(getattr(mode, "enter")):
            self.current_mode.enter(self)


class Mode:
    def __init__(self, ui):
        self.ui = ui

    def locked(self):
        return False

class ExitMode(Mode):
    def __init__(self, ui):
        self.ui = ui

    def evaluate(self, text):
        return text == 'x'

    def enter(self, stateMachine):
        raise urwid.ExitMainLoop()
        self.stop()

    def __str__(self):
        return "ExitMode"

class RunMode(Mode):
    def __init__(self, ui):
        self.ui = ui

    def evaluate(self, text):
        return text == 'r' and self.ui.debugger.is_connected()

    def enter(self, stateMachine):
        self.ui.debugger.execute_operation(debugger.RunOperation(self.ui.debugger, self.handleRun))

    def handle_run(self, state):
        if state.status == "status":
            self.ui.print_message("Breakpoint triggered at line {0}".format(state.line_number))
            if (self.ui.current_file != state.file):
                self.ui.print_message(state.file_name)
                self.ui.print_file(state.file_name, self.debugger.open_file(state.file_name, True), self.debugger.get_breakpoints(state.file_name))
            self.debugger.ui.trigger_breakpoint(state.line_number)
            self.debugger.ui.print_context(state.context_names, state.context)
        else:
            self.debugger.ui.print_message("Status: {0}".format(state.status))

    def __str__(self):
        return "RunMode"

class FileExplorerMode(Mode):
    def __init__(self, ui):
        self.ui = ui

    def evaluate(self, text):
        return self.ui.frame.focus_part == 'body' and (not text or text == 'down' or text == 'up' or text == ' ') and self.ui.file_loaded

    def handle_input(self, text):
        if text == ' ':
            focused, position = self.ui.content.get_focus()
            focused.set_attr_map({ None: 'streak' })
            position += 1
            self.ui.debugger.add_breakpoint(debugger.LineBreakPoint(self.ui.file_name, position))
            self.ui.print_message("Breakpoint set at line {0}".format(position))

    def __str__(self):
        return "FileExplorerMode"

class OpenFileMode(Mode):
    """
    This mode handles input of a file path. It then finished by opening it and,
    then switches to the previous mode.
    """
    def __init__(self, ui):
        self.ui = ui

    def evaluate(self, text):
        return text == "o"

    def locked(self):
        """
        This mode is locked until it releases itself.
        """
        return True

    def enter(self, state_machine):
        self.machine = state_machine
        self.ui.input.set_caption(u"Path to file:")
        self.ui.frame.set_focus('footer')
        urwid.connect_signal(self.ui.input, 'change', self.handle_text_input)

    def handle_text_input(self, edit, text):
        assert edit is self.ui.input
        self.file = text

    def handle_input(self, text):
        if text == "enter":
            # When we catch an enter command, swap the focus.
            self.ui.frame.set_focus('body')
            self.ui.print_file(self.file, self.ui.debugger.open_file(self.file, True), {})
            self.ui.input.set_caption(u"")
            self.ui.input.set_edit_text(u"")
            self.ui.print_message("Opened file {0}".format(self.file))
            self.machine.set_previous_mode()

    def __str__(self):
        return "OpenFileMode"
