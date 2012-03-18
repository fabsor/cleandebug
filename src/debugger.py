import SocketServer
import threading
from xml.dom.minidom import parseString
from base64 import b64encode, b64decode
from pprint import PrettyPrinter
import os

class DBGPThread(threading.Thread):
    def __init__(self, connection, connection_fn):
        threading.Thread.__init__(self)
        self.server = DBGPServer(connection, connection_fn)

    def run(self):
        self.server.serve_forever()

    def stop(self):
        self.server.shutdown()


class DBGPServer(SocketServer.TCPServer):
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
        return self.execute_command(command).getElementsByTagName("response")[0].getAttribute('id')

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
        return self.execute_command("status -i {0}\0".format(self.transaction_id)).getElementsByTagName("response")[0].getAttribute('status')

    def run(self):
        result = self.execute_command("run -i {0}\0".format(self.transaction_id))
        response = result.getElementsByTagName("response")[0]
        data = { 'status': response.getAttribute('status') }
        if data['status'] == u'break':
            breakpoint = result.getElementsByTagName("xdebug:message")[0]
            data = {'status': data['status'], 'filename': breakpoint.getAttribute('filename'), 'lineno': int(breakpoint.getAttribute('lineno')) }
        return data

    def get_context_names(self, stack_depth = None):
        """
        Get the contexts that are currently available.
        """
        result = self.execute_command("context_names -i {0}\0".format(self.transaction_id))
        contexts = []
        for context_element in result.getElementsByTagName("context"):
            contexts.append({"name": context_element.getAttribute("name"), "id": int(context_element.getAttribute("id"))});
        return contexts

    def get_context(self, context_id = 0, stack_depth = None):
        """
        Get the current context.
        """
        result = self.execute_command("context_get -d {0} -i {1}\0".format(stack_depth, self.transaction_id));
        properties = {}
        for property_element in result.getElementsByTagName("property"):
            dbg_property = {}
            for name in ["name", "fullname", "data_type", "classname", "constant", "children", "size", "page", "pagesize", "address", "key", "encoding", "numchildren"]:
                dbg_property[name] = property_element.getAttribute(name)
            #dbg_property["data"] = b64decode(property_element.nodeValue)
            properties[dbg_property["fullname"]] = dbg_property
        return properties

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
        self.thread = None
        self.running = False
        self.connected = False
        self.breakpoints = {}
        self.operations = []
        self.operation_event = threading.Event()
        self.operation_lock = threading.Lock()
        ui.set_debugger(self)

    def add_breakpoint(self, breakpoint):
        if not breakpoint.file_name in self.breakpoints.keys():
            self.breakpoints[breakpoint.file_name] = []
        self.breakpoints[breakpoint.file_name].append(breakpoint)

    def is_connected(self):
        return self.connected

    def start(self):
        self.thread = DBGPThread((self.host, int(self.port)), self.handle_connection)
        self.ui.print_message(u"Listening")
        self.thread.start()

    def stop(self):
        self.disconnect()
        self.ui.print_message("SHUTTING DOWN")
        if self.thread:
            self.thread.stop()
        self.ui.stop()

    def execute_operation(self, operation):
        """
        Add an operation that is to be executed in the current connection.
        """
        with self.operation_lock:
            self.operations.append(operation)
        self.operation_event.set()

    def handle_connection(self, con):
        self.con = con
        self.connected = True
        file_name = self.find_file(con.fileUri)
        self.ui.print_message("Connected!".format(con.session))
        self.ui.print_file(file_name, self.open_file(file_name, True))
        # Add all breakpoints
        for file in self.breakpoints.itervalues():
            for breakpoint in file:
                result = breakpoint.execute(self.create_client_path, self.con)
        self.run()

    def run(self):
        """
        Run loop.
        """
        while self.connected:
            self.execute_operations()
            self.operation_event.wait()

    def execute_operations(self):
        """
        Execute all queued operations.
        """
        while len(self.operations) > 0:
            with self.operation_lock:
                item = self.operations.pop();
            item.run()

    def disconnect(self):
        """
        Disconnect from the current connection
        """
        self.connected = False
        self.con = None

    def create_client_path(self, file_path):
        return "{0}/{1}".format(self.client_base_path, file_path)

    def find_file(self, file_uri):
        # Split the path into path
        parts = str(file_uri).split('/')
        # Go down the path until we find the common base directory.
        # The first three parts are useless since the return values of dbgp
        # are file:///.
        for i, part in enumerate(reversed(parts[3:])):
            current_path = "{0}/{1}".format(self.base_path, part)
            if os.path.exists(current_path):
                position = len(parts)-(i+1)
                self.client_base_path = '/'.join(parts[0:position])
                # return the relative path, it's easier to work with when setting breakpoints.
                return '/'.join(parts[position:])
        return False

    def open_file(self, file, relative=False):
        if relative:
            file = "{0}/{1}".format(self.base_path, file)
        try:
            handle = open(file)
            return handle.read()
        except:
            return False

class LineBreakPoint:
    """
    This class represents a line breakpoint.
    """
    def __init__(self, file_name, line_number):
        self.file_name = file_name
        self.line_number = line_number
        self.enabled = True

    def toggle(self):
        self.enabled = not self.enabled

    def execute(self, base_path_fn, con):
        result = con.execute_command("breakpoint_set -i {0} -t {1} -n {2} -f {3} -r {4}\0".format(con.transaction_id, "line",                                                                      self.line_number, base_path_fn(self.file_name), int(self.enabled)))
        self.id = result.getElementsByTagName("response")[0].getAttribute('id')

class RunOperation():
    def __init__(self, debugger):
        self.debugger = debugger

    def run(self):
        result = self.debugger.con.run()
        if result['status'] == u"break":
            self.debugger.ui.print_message("Breakpoint triggered at line {0}".format(result['lineno']))
            context_names = self.debugger.con.get_context_names()
            context = self.debugger.con.get_context()
            current_file = self.debugger.find_file(result['filename'])
            if (self.debugger.ui.file_name != current_file):
                #self.debugger.ui.print_message(current_file)
                self.debugger.ui.print_file(current_file, self.debugger.open_file(current_file, True), self.debugger.breakpoints[current_file])
            self.debugger.ui.trigger_breakpoint(result['lineno'])
            self.debugger.ui.print_context(context_names, context)
        else:
            self.debugger.ui.print_message("Status: {0}".format(result['status']))
