import SocketServer
import threading
from xml.dom.minidom import parseString
from base64 import b64encode, b64decode
from pprint import PrettyPrinter
from io import *
import os

class ThreadConnectionHandler(threading.Thread):
    """
    This connection handler uses a thread for handling server connections,
    and connects using over TCP.
    """
    def __init__(self, connection):
        threading.Thread.__init__(self)

    def set_connection_handler(connection_fn):
        """
        Set the connection handler (the function to call when new connections are coming ing in) to use.
        >>> handler = mock.MockConnectionHandler()
        >>> connection_fn = lambda(con): True
        >>> handler.set_connection_handler(connection_fn)
        >>> handler.connection_fn is connection_fn
        True
        """
        self.connection_fn = connection_fn
        self.server = DBGPServer(connection, connection_fn)

    def run(self):
        self.server.serve_forever()

    def stop(self):
        self.server.shutdown()


class DBGPServer(SocketServer.TCPServer):
    """
    A TCP Server suitable for handling dbgp connections.
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
    >>> connection = mock.MockedTCPConnection(mock.xdebug_init)
    >>> con = DebuggerConnection(connection, 1)
    >>> con.idekey
    u'IDE_KEY'
    >>> con.session
    u'DBGP_COOKIE'
    >>> con.parent
    u'PARENT_APPID'
    >>> con.language
    u'LANGUAGE_NAME'
    >>> con.protocol_version
    u'1.0'
    >>> con.file_uri
    u'file://path/to/file'
    """
    def __init__(self, connection, transaction_id):
        self.connection = connection
        self.transaction_id = transaction_id
        self.breakpoints = {}
        self.initialize()

    def execute_command(self, command):
        """
        Execute a particular command on the connected debugger.
        >>> connection = mock.MockedTCPConnection(mock.xdebug_init)
        >>> debugger = DebuggerConnection(connection, 1)
        >>> connection.set_payload(mock.xdebug_starting)
        >>> dom = debugger.execute_command("status -i 1")
        >>> dom.toxml()
        u'<?xml version="1.0" ?><response command="status" reason="ok" status="starting" transaction_id="transaction_id"/>'
        """
        self.connection.sendall(command)
        return self.receive()

    def receive(self):
        """
        Receive data and create a dom object.
        """
        data = self.connection.recv(self.receive_size())
        self.connection.recv(1)
        dom = parseString(data)
        return dom

    def receive_size(self):
        """
        Receive the total size of the dbgp response.
        >>> connection = mock.MockedTCPConnection(mock.xdebug_init)
        >>> debugger = DebuggerConnection(connection, 1)
        >>> connection.set_payload(mock.xdebug_starting)
        >>> debugger.receive_size()
        100
        """
        val = ''
        size = ''
        while val != '\0':
            val = self.connection.recv(1)
            if val != '\0':
                size += val
        return int(size)

    def status(self):
        """
        Execute a status message and return the status of the message.
        >>> connection = mock.MockedTCPConnection(mock.xdebug_init)
        >>> debugger = DebuggerConnection(connection, 1)
        >>> connection.set_payload(mock.xdebug_starting)
        >>> debugger.status()
        u'starting'
        """
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
        >>> connection = mock.MockedTCPConnection(mock.xdebug_init)
        >>> debugger = DebuggerConnection(connection, 1)
        >>> connection.set_payload(mock.xdebug_context_names)
        >>> debugger.get_context_names()
        [{'name': u'Local', 'id': 0}, {'name': u'Global', 'id': 1}, {'name': u'Class', 'id': 2}]
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
        self.protocol_version = init.getAttribute('protocol_version')
        self.file_uri = init.getAttribute('fileuri')
        self.initialized = True

class Debugger:
    """
    The debuggger class is the main class that can be used to listen for
    dbgp connections on a given port.
    >>> debugger = Debugger('.')
    """
    def __init__(self, base_path, host, port, io_wrapper=OSIOWrapper()):
        """
        @param base_path: the path from which the debugger should look for files.
        """
        self.base_path = base_path
        self.thread = None
        self.running = False
        self.connected = False
        self.io_wrapper = io_wrapper
        self.breakpoints = {}
        self.operations = []
        self.operation_event = threading.Event()
        self.operation_lock = threading.Lock()
        self.handler = None
        self.host = host
        self.port = port

    def add_breakpoint(self, breakpoint):
        """
        Add a breakpoint
        @param breakpoint: the breakpoint to add.
        >>> debugger = Debugger(".")
        >>> breakpoint = LineBreakPoint("index.php", 1)
        >>> debugger.add_breakpoint(breakpoint)
        >>> debugger.breakpoints.keys()
        ['index.php']
        >>> debugger.breakpoints['index.php'][0] == breakpoint
        True
        """
        if not breakpoint.file_name in self.breakpoints.keys():
            self.breakpoints[breakpoint.file_name] = []
        self.breakpoints[breakpoint.file_name].append(breakpoint)

    def get_breakpoints(self, file_name):
        """
        Get all breakpoints in a certain file.
        >>> debugger = Debugger(".")
        >>> breakpoint = LineBreakPoint("index.php", 1)
        >>> debugger.add_breakpoint(breakpoint)
        >>> debugger.get_breakpoints("index.php")[0] == breakpoint
        True
        """
        return self.breakpoints[file_name]

    def is_connected(self):
        """
        Check if the debugger has a active connection to a client.
        #>>> debugger = Debugger(".")
        #>>> debugger.is_connected()
        #False
        #>>> connection_handler = mock.MockConnectionHandler()
        #>>> debugger.start(connection_handler)
        #>>> connection_handler.trigger_connection()
        #>>> debugger.is_connected()
        #True
        """
        return self.connected

    def start(self):
        """
        Start listening for connections.
        >>> debugger = Debugger(".")
        >>> connection_handler = mock.MockConnectionHandler()
        >>> debugger.start(connection_handler)
        >>> connection_handler.started
        True
        """
        return
        self.handler = connection_handler
        connection_handler.set_connection_handler(self.handle_connection)
        self.handler.start()

    def stop(self):
        """
        Stop listening for connections.
        >>> debugger = Debugger(".")
        >>> connection_handler = mock.MockConnectionHandler()
        >>> debugger.start(connection_handler)
        >>> debugger.stop()
        >>> connection_handler.started
        False
        """
        self.disconnect()
        if self.handler:
            self.handler.stop()

    def execute_operation(self, operation):
        """
        Add an operation that is to be executed in the current connection.
        """
        with self.operation_lock:
            self.operations.append(operation)
        self.operation_event.set()

    def handle_connection(self, con):
        """
        Handle an incoming connection.
        This will process the queue of operations to perform.
        @con: An open dbgp connection.
        """
        self.con = con
        self.connected = True
        self.create_client_base_path(con.file_uri)
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
        """
        Create a client path to a particular file.
        >>> debugger = Debugger('.')
        >>> debugger.client_base_path = 'file://path/to/my/server/files'
        >>> debugger.create_client_path("index.php")
        u'file://path/to/my/server/files/index.php'
        """
        return u'{0}/{1}'.format(self.client_base_path, file_path)

    def create_client_base_path(self, file_uri):
        """
        Create the client base path based on the a current file URI and the
        current base path used.
        @param file_uri: A file URI from the debugger.
        >>> wrapper = MockIOWrapper(['/my/local/files/index.php'])
        >>> debugger = Debugger('/my/local/files', wrapper)
        >>> debugger.create_client_base_path('file://path/to/my/server/files/index.php')
        u'file://path/to/my/server/files'
        """
        # Split the path into path
        parts = str(file_uri).split('/')
        # Go down the path until we find the common base directory.
        # The first three parts are useless since the return values of dbgp
        # are file:///.
        for i, part in enumerate(reversed(parts[3:])):
            current_path = u'{0}/{1}'.format(self.base_path, part)
            if self.io_wrapper.exists(current_path):
                position = len(parts)-(i+1)
                self.client_base_path = unicode('/'.join(parts[0:position]))
                return self.client_base_path
        return False

    def find_file(self, file_uri):
        """
        Find a file on the local file system based on a debugger path.
        >>> debugger = Debugger('/my/local/files')
        >>> debugger.client_base_path = 'file://path/to/my/server'
        >>> debugger.find_file('file://path/to/my/server/index.php')
        u'/index.php'
        """
        # Split the path into path
        return unicode(file_uri).split(self.client_base_path)[1]

    def open_file(self, file, relative=False):
        """
        Open a particular file and read it's contents.
        @return: The file contents in a string or False if the file could not
        be found.
        """
        if relative:
            file = u"{0}/{1}".format(self.base_path, file)
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
        """
        Toggle a breakpoint on and off.
        """
        self.enabled = not self.enabled

    def execute(self, base_path_fn, con):
        """
        Execute the command on the server.
        >>> breakpoint = LineBreakPoint("index.php", 1)
        >>>
        """
        result = con.execute_command("breakpoint_set -i {0} -t {1} -n {2} -f {3} -r {4}\0".format(con.transaction_id, "line",                                                                      self.line_number, base_path_fn(self.file_name), int(self.enabled)))
        self.id = result.getElementsByTagName("response")[0].getAttribute('id')

class DebuggerState:
    """
    This class represents the debugger state.
    """
    def __init__(status, file_name, line_number = 0, context_names = [], context = {}):
        self.status = status
        self.file_name = file_name
        self.context_names = context_names
        self.context = context
        self.line_number = line_number

class RunOperation:
    """
    This operation tells the debugger to run until it hits a breakpoint or
    the end of the exection.
    """
    def __init__(self, debugger, callback_fn):
        self.debugger = debugger
        self.callback_fn = callback_fn

    def run(self):
        result = self.debugger.con.run()
        context_names = self.debugger.con.get_context_names()
        context = self.debugger.con.get_context()
        current_file = self.debugger.find_file(result['filename'])
        return DebuggerState(str(result['status']), current_file, context_names, context)

class ChangeContextOperation:
    """
    Change the context and get the relevant information.
    """
    def __init__(self, debugger, context_id, callback_fn):
        self.debugger = debugger
        self.callback_fn = callback_fn

    def run(self):
        context_names = self.debugger.con.get_context(context_id)
        self.callback_fn(context_names)

if __name__ == "__main__":
    import doctest
    import mock
    doctest.testmod()
