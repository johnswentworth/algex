import uuid

class BaseSymbol:
    pass

class S(BaseSymbol):
    def __init__(self, s):
        self.s = s
    
    def __hash__(self):
        return self.s.__hash__()
    
    def __eq__(self, other):
        return isinstance(other, S) and self.s == other.s
    
    def __repr__(self):
        return "S('" + self.s + "')"

class InternalSymbol(S):
    def __init__(self, s=None):
        if s is None:
            self.s = str(uuid.uuid4())
        else:
            self.s = str(s)
