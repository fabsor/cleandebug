"""
A set of mocked classes that can be used to test debugger functionality.
"""

class MockedTCPConnection:
    """
    A mocked TCP Connection object.
    """
    def __init__(self, payload = ""):
        self.payload = payload
        self.pointer = 0

    def sendall(self, data):
        pass

    def send(self, data):
        pass

    def set_payload(self, payload):
        self.payload = payload
        self.pointer = 0

    def recv(self, length = None):
        if not length:
            return self.payload
        else:
            data = self.payload[self.pointer:self.pointer+length]
            self.pointer += length
            return data 

"""
An example init command.
"""
xdebug_init = '185\0<init appid="APPID" idekey="IDE_KEY" session="DBGP_COOKIE" thread="THREAD_ID" parent="PARENT_APPID" language="LANGUAGE_NAME" protocol_version="1.0" fileuri="file://path/to/file"></init>\0'

xdebug_starting = '100\0<response command="status" status="starting" reason="ok" transaction_id="transaction_id"></response>\0'

xdebug_stopping = '100\0<response command="status" status="stopping" reason="ok" transaction_id="transaction_id"></response>\0'

xdebug_context_names = '168\0<response command="context_names" transaction_id="transaction_id"><context name="Local" id="0"/><context name="Global" id="1"/><context name="Class" id="2"/></response>\0'

class MockConnection:
    """
    A fake connection that can be used for tests.
    """
    def __init__(self):
        self.file_uri = "file://path/to/file"

class MockConnectionHandler(threading.Thread):
    """
    A mock connection handler that doesn't connect anywhere.
    """
    def __init__(self):
        """
        >>> handler = MockConnectionHandler()
        >>> handler.started
        False
        """
        self.started = False

    def set_connection_handler(self, connection_fn):
        """
        Set the connection handler.
        >>> handler = mock.MockConnectionHandler()
        >>> connection_fn = lambda(con): True
        >>> handler.set_connection_handler(connection_fn)
        >>> handler.connection_fn is connection_fn
        True
        """
        self.connection_fn = connection_fn

    def run(self):
        """
        Start the thread by calling the connection function.
        >>> con = MockConnectionHandler()
        >>> con.run()
        >>> con.started
        True
        """
        self.started = True
        self.connection_fn(MockConnection())

    def stop(self):
        self.started = False

def create_fake_connection():
    """
    Create a fake connection that can be used to test things requiring a ocnnection.
    """
    connection = mock.MockedTCPConnection(mock.xdebug_init)
    con = DebuggerConnection(connection, 1)
    return con

class MockOperation:
    """
    A mock operation class
    """
    def init(self):
        self.executed = False
    def execute():
        self.executed = True
