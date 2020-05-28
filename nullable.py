from symbol import InternalSymbol
from misc import root
from sqlizer import get_symbol_directory
from error_handler import ErrorHandler

class Nullable(ErrorHandler):
    def __init__(self, x):
        self.symbol_directory = get_symbol_directory(x)
        super().__init__(x)
    
    def handle_error(self, error, intermediate, current_table, rhs):
        for table, symbols in self.symbol_directory.items():
            if table == root:
                continue
            solution = {symbol: None for symbol in symbols}
            parent_row = intermediate.size(intermediate.parents[table])
            solution[InternalSymbol('_parent_id')] = parent_row
            
            intermediate.append(table, solution)
        return {symbol: None for symbol in self.symbol_directory[root]}
    
    def __repr__(self):
        return 'Nullable(' + self.x.__repr__() + ')'
