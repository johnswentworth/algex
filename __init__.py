from symbol import S
from transform import Transform
from error_handler import ErrorHandler
from nullable import Nullable

from intermediate import MemoryIntermediate
from solver import solver, Eqn
from substitute import substitute

def solve(template, data):
    if not isinstance(template, list):
        # Outermost level should always be wrapped in a list
        template = [template]
        data = [data]
    
    intermediate = MemoryIntermediate()
    return solver(Eqn(template, data), intermediate)
