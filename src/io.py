"""
Wrappers for IO operations.
"""
from os import path

class MockIOWrapper:
    """
    Fake IO Wrapper that will work with all paths specified in the consstructor.
    >>> paths = ['/my/path']
    >>> wrapper = MockIOWrapper(paths)
    >>> wrapper.existing_paths is paths
    True
    """
    def __init__(self, existing_paths):
        self.existing_paths = existing_paths

    """
    Fake IO wrapper that just returns true
    """
    def exists(self, path):
        """
        Return true
        >>> wrapper = MockIOWrapper(['my/path'])
        >>> wrapper.exists('my/path')
        True
        """
        return path in self.existing_paths

    def read_file(self, file_path):
        """
        Open a partiuclar file path.
        >>> wrapper = MockIOWrapper(['example'])
        >>> wrapper.read_file('example')
        u'example data'
        """
        if exists(path):
            return u'example data'
        else:
            raise IOError("Could not read file")

class OSIOWrapper:
    """
    OS IO wrapper using the IO operations of the Operating system.
    >>> wrapper = OSIOWrapper()
    >>> wrapper.exists is path.exists
    True
    """
    def __init__(self):
        self.exists = path.exists
    
    def read_file(self, path):
        """
        Open a partiuclar file path.
        >>> wrapper = OSIOWrapper()
        >>> wrapper.open("example")
        u'example data'
        """
        with open(path) as handle:
            return handle.read()
