from .symbol import BaseSymbol

class ErrorHandler(BaseSymbol):
    def __init__(self, x):
        self.x = x
    
    def handle_error(self, error, rhs):
        raise Exception("ErrorHandlers must implement handle_error()")
