"""Defines exception classes for mureil operations.
"""

class MureilException(Exception):
    pass

class AlgorithmException(MureilException):
    """Exception raised for errors found while running the algorithm.

    Attributes:
        msg  -- explanation of the error
        data -- a dict of any useful information to understand the error
    """

    def __init__(self, msg, data):
        self.msg = msg
        self.data = data


class ConfigException(MureilException):
    """Exception raised for problems in building and configuring.
    
    Attributes:
        msg -- explanation of the error
        source -- the file where the exception occurred
        data -- a dict of any useful information to understand the error
    """
    
    def __init__(self, msg, source, data):
        self.msg = msg
        self.source = source
        self.data = data
        

class ClassTypeException(MureilException):
    """Exception raised when selected class does not implement required
    sub-class.
    
    Attributes:
        msg -- explanation of the error
        source -- the file where the exception occurred
        class_name -- the name of the class instantiated
        subclass_name -- the name of the class it should have implemented
        data -- a dict of any useful information to understand the error
    """
    
    def __init__(self, msg, source, class_name, subclass_name, data):
        self.msg = msg
        self.source = source
        self.class_name = class_name
        self.subclass_name = subclass_name
        self.data = data
        
        