from .symbol import BaseSymbol

def identity(x):
    return x

class Transform(BaseSymbol):
    def __init__(self, x, function=identity, inverse=identity):
        if isinstance(function, dict):
            f_d = function
            function = lambda x: f_d[x]
        if isinstance(inverse, dict):
            i_d = inverse
            inverse = lambda x: i_d[x]
        
        self.x = x
        self.f = function
        self.inv = inverse
    
    def __hash__(self):
        # TODO: do something better than this
        return id(self)
    
    def __eq__(self, other):
        return isinstance(other, Transform) and (self.x, self.f, self.inv) == (other.x, other.f, other.inv)
