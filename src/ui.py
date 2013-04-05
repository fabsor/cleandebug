import pygtk
pygtk.require('2.0')
import gtk
import gtksourceview2

import debugger
from pprint import PrettyPrinter
from debugger import LineBreakPoint

def start():
    gtk.main()

class BaseWindow:
    def __init__(self, title, size=(640,480)):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)

        self.window.connect("delete_event", self.__gtk_delete__)
        self.window.connect("destroy", self.__gtk_destory__)
        self.window.set_title(title)
        self.window.set_default_size(size[0], size[1])
        self.window.set_border_width(10)

    # Callbacks
    def __gtk_delete__(self, widget, event, data=None):
        # Change FALSE to TRUE and the main window will not be destroyed
        # with a "delete_event".
        return False

    def __gtk_destory__(self, data=None):
        gtk.main_quit() # Only for the main window.


class MainWindow(BaseWindow):
    def __init__(self, debugger):
        BaseWindow.__init__(self, "Clean Debug")

        self.debugger = debugger

        codebox = gtk.HBox(spacing=5)
        self.window.add(codebox)

        # Code area
        # Set syntax high lightning
        self.codebuffer = gtksourceview2.Buffer()
        #codebuffer.set_text(open("sample.php",'r').read())
        # To get all available: gtksourceview2.language_manager_get_default().get_language_ids()

        self.codebuffer.set_language(gtksourceview2.language_manager_get_default().get_language('php')) # FIXME: add an menu later on for this
        self.codebuffer.set_highlight_syntax(True)

        self.text = gtksourceview2.View(self.codebuffer)
        self.text.set_show_line_numbers(True)

        codebox.add(self.text)

        self.button = gtk.Button("Hello")
        codebox.add(self.button)
        self.window.show_all()

    def open_file(path, string=None):
        """Set the buffer to file contents or an string"""
        if string:
            self.codebuffer.set_text(string)

        self.codebuffer.set_text(open(path, 'r').read())


class HelloDialog:
    def __init__(self):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)

        self.window.connect("delete_event", self.__gtk_delete__)
        self.window.connect("destroy", self.__gtk_destory__)

        self.window.set_border_width(10)

        self.button = gtk.Button("Hello World")
        self.button.connect("clicked", self.__button_hello__, None)

        self.window.add(self.button)
        self.button.show()
        self.window.show()

    # Callbacks
    def __gtk_delete__(self, widget, event, data=None):
        # Change FALSE to TRUE and the main window will not be destroyed
        # with a "delete_event".
        return False

    def __gtk_destory__(self, data=None):
        gtk.main_quit() # Only for the main window.

    def __button_hello__(self, widget, event, data=None):
        print "Yes"



