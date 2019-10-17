from symbol import BaseSymbol, S, InternalSymbol
from transform import Transform

from inspect import signature
from collections import namedtuple, OrderedDict
from functools import reduce

try:
    import pandas as pd
except ModuleNotFoundError as e:
    # TODO: fallback
    raise e

class Everything:
    # Screw you Russell
    def __contains__(self, item):
        return True
everything = Everything()

def wrap(rule):
    def new_rule(tree, walk):
        return rule(tree)
    return new_rule

class TreeWalk:
    def __init__(self, cases):
        case_list = []
        for condition, rule in cases:
            sig = signature(rule)
            if len(sig.parameters) == 1:
                rule = wrap(rule)
            case_list.append((condition, rule))
        self.cases = OrderedDict(case_list)
    
    def walk(self, tree):
        for condition, rule in self.cases.items():
            if condition(tree):
                return rule(tree, self.walk)
        return tree  # If you want a particular default, then make a catch-all case
    
    def __call__(self, tree):
        return self.walk(tree)

class NoMatchException(Exception):
    pass

# TODO: cleaner format. Rather than nesting tables, use a foreign key setup to link to conceptually "nested" tables.
Eqn = namedtuple('Equation', ['lhs', 'rhs'])
class Solver(TreeWalk):
    def solve_symbol(eqn):
        return {eqn.lhs: eqn.rhs}
    
    def solve_transform(eqn, solve):
        # We have f(x) = rhs, so to solve it, we solve x = inv(rhs)
        return solve(Eqn(eqn.lhs.x, eqn.lhs.inv(eqn.rhs)))
    
    def solve_dict(eqn, solve):
        # NOTE: need to handle same-symbol conflicts
        # TODO: type check RHS
        solution = {}
        for k, v in eqn.lhs.items():
            # TODO: implement Nullable and handle missing stuff in general
            solution.update(solve(Eqn(v, eqn.rhs.get(k, None))))
        return solution
    
    def solve_list(eqn, solve):
        # TODO: type check RHS & handle single item
        
        # Each entry of eqn.lhs is actually independent, but we only want to walk
        # eqn.rhs once (to handle streams), so we handle all the eqn.lhs entries
        # inside of the eqn.rhs loop.
        solutions = [[] for lhs in eqn.lhs]
        for rhs in eqn.rhs:
            for ind, lhs in enumerate(eqn.lhs):
                try:
                    solutions[ind].append(solve(Eqn(lhs, rhs)))
                except NoMatchException:
                    continue
        for ind, subsolutions in enumerate(solutions):
            if not subsolutions:
                raise NoMatchException('No match found for:', eqn.lhs[ind])
        # NOTE: using id on rhs would be Bad, because streams, but lhs is fine.
        return {InternalSymbol(id(lhs)): pd.DataFrame(solutions[ind]) for ind, lhs in enumerate(eqn.lhs)}
    
    def check_match(eqn):
        if eqn.lhs != eqn.rhs:
            raise NoMatchException('LHS does not match data:', eqn.lhs)
        return {}
        
    def __init__(self):
        super().__init__([
            (lambda eqn: isinstance(eqn.lhs, S), Solver.solve_symbol),
            (lambda eqn: isinstance(eqn.lhs, Transform), Solver.solve_transform),
            (lambda eqn: isinstance(eqn.lhs, dict), Solver.solve_dict),
            (lambda eqn: isinstance(eqn.lhs, list), Solver.solve_list),
            (lambda eqn: True, Solver.check_match)])
solver = Solver()

    
def solve_direct(lhs, rhs, symbols=everything, constraints={}):
    # symbols are the symbols we wish to solve for; constraints are fixed symbol values (mainly used for repeated/recursive calls so we can re-use table tree)
    # Step 1: build tree of Tables, containing solved values from the data
    table_tree = solver(Eqn(lhs, rhs))
    # TODO: if a dict is returned, make it a table
    
    # Step 2: handle equality constraints on repeated symbols
    # This is where there's room to be smart, but for now we're going to skip it altogether (so join symbols need to be in query!).
    
    # Step 3: filter on constraints & take cartesian product
    
    return Solution(lhs, rhs)

data = [{'name': 'john', 'addresses': [{'state': 'CA'}, {'state': 'CT'}], 'houses':[{'state': 'CT'}]},
        {'name': 'allan', 'addresses': [{'state': 'CA'}, {'state': 'WA'}], 'houses':[{'state': 'WA'}]}]
match_template = [{'name': S('name'), 'addresses': [{'state': S('state')}], 'houses':[{'state': S('state')}]}]
