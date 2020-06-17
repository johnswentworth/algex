from .symbol import InternalSymbol
root = InternalSymbol('root')

class NoMatchException(Exception):
    pass

def table_name(obj):
    return InternalSymbol('T' + str(id(obj)))
    #return 'T' + str(obj.__hash__())