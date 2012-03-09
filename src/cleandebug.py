import socket
import SocketServer
from xml.dom.minidom import parse, parseString
from base64 import b64encode
import argparse
import os
import curses

class DBGPServer(SocketServer.TCPServer):
    """
    A DBGP server class that can be used by any client to get notified about commands.
    """
    def __init__(self, connection, connection_fn):
        SocketServer.TCPServer.__init__(self, connection, DBGPTCPHandler)
        self.connection_fn = connection_fn


class DBGPTCPHandler(SocketServer.BaseRequestHandler):
    """
    A DBGP TCP handler, dealing with request following the DPBP protocol.
    """
    def handle(self):
        # @todo, generate unique ID.
        self.transaction_id = 1;
        dbgp = DebuggerConnection(self.request, self.transaction_id)
        self.server.connection_fn(dbgp)
                
class DebuggerConnection:
    """
    This is an implementation of the DBGP protocol.
    """
    def __init__(self, connection, transaction_id):
        self.connection = connection
        self.transaction_id = transaction_id
        self.breakpoints = {}
        self.initialize()

    def set_breakpoint(self, file, lineNumber=-1, type="line", state="enabled", function=None, exception=None, hit_value=0, hit_condition=None, temporary=0, expression=None):
        """
        Set a breakpoint
        @return: The id of the newly set breakpoint.
        """
        command = "breakpoint_set -i {0} -t {1} -n {2} -f {3} -r {4}\0".format(self.transaction_id, type, lineNumber, file, state) 
        if function:
            command = "{0} -m {1}".format(command, function)
        if exception:
            command = "{0} -x {1}".format(command, function)
        if hit_value:
            command = "{0} -h {1}".format(command, hit_value)
        if hit_condition:
            command = "{0} -o {1}".format(command, hit_condition)
        if temporary:
            command = "{0} -r {1}".format(command, hit_condition)
        if expression:
            command = "{0} -- {1}".format(command, b64encode(hit_condition))
        id = self.execute_command(command).getElementsByTagName("response")[0].getAttribute('id')
        self.breakpoints[id] = id
        return id
        
    def execute_command(self, command):
        self.connection.sendall(command)
        return self.receive()
        
    def receive(self):
        data = self.connection.recv(self.receive_size())
        self.connection.recv(1)
        dom = parseString(data)
        return dom

    def receive_size(self):
        val = ''
        size = ''
        while val != '\0':
            val = self.connection.recv(1)
            if val != '\0':
                size += val
        return int(size)

    def status(self):
        return self.execute_command("status -i {}\0".format(self.transaction_id)).getElementsByTagName("response")[0].getAttribute('status')

    def run(self):
        return self.execute_command("run -i {}\0".format(self.transaction_id)).getElementsByTagName("response")[0].getAttribute('status')

    def initialize(self):
        dom = self.receive()
        init = dom.getElementsByTagName("init")[0]
        self.idekey = init.getAttribute('idekey')
        self.session = init.getAttribute('session')
        self.thread = init.getAttribute('thread')
        self.parent = init.getAttribute('parent')
        self.language = init.getAttribute('language')
        self.protocolVersion = init.getAttribute('protocol_version')
        self.fileUri = init.getAttribute('fileuri')
        self.initialized = True

class Debugger:
    def __init__(self, base_path, ui, port=9000, host="127.0.0.1"):
        self.base_path = base_path 
        self.ui = ui
        self.port = 9000
        self.host = host
        
    def listen(self):
        server = DBGPServer((host, int(args.port)), self.handleConnection)
        self.ui.print_message("Listening on {}:{}".format(self.host, self.port))
        server.serve_forever()
        
    def handleConnection(self, con):
        self.con = con
        file = self.find_file(con.fileUri)
        self.ui.print_file(file, self.open_file(file))
        action = self.ui.prompt()

    def find_file(self, fileUri):
        # Split the path into path
        parts = str(fileUri).split('/')
        # Go down the path until we find the common base directory.
        # The first three parts are useless since the return values of dbgp
        # are file:///.
        for i in range(len(parts[3:])):
            current_path = "{}/{}".format(self.base_path, parts[i+3])
            if os.path.exists(current_path):
                return current_path
        return False
    
    def open_file(self, file):
        try:
            handle = open(file)
            return handle.read()
        except:
            return False

class DebuggerOperation:
    """
    Represents an operation that can be chosen by the user to be executed.
    """
    def __init(self, debugger, name, operation, *params):
        self.debugger = debugger
        self.name = name
        self.operation = operation
        self.params = params
    def run(self):
        self.operation(params)

class RunOperation(DebuggerOperation):
    
    def __init(self, debugger, name):
        DebuggerOperation.__init(self, debugger, name)
    

class CursesUI:
    """
    A curses UI for the debugger.
    """
    def __init__(self, operations):
        self.scr = curses.initscr()
        self.operations = {}
        curses.cbreak()
        self.scr.keypad(1)
    
       
    def menu(self):
        return ["(O)pen file", "(E)xit", "<SPACE> Set breakpoint", "(R)un"];
        
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
        if (result == "o"):
            self.print_message("Enter the path to the file to open")
        
    def __del__(self):
        curses.nocbreak()
        self.scr.keypad(0)
        curses.echo()
        curses.endwin()      

if __name__ == "__main__":               
    parser = argparse.ArgumentParser('dbgp debugger for PHP scripts.')
    parser.add_argument('--port', action='store', default=9000, help='Port (defaults to 9000)')
    parser.add_argument('path', action='store', help="The directory to look for scripts in.", default='.')
    host = "127.0.0.1"
    args = parser.parse_args()
    debugger = Debugger(args.path, CursesUI(), args.port)
    debugger.listen()
