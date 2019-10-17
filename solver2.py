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

root = 'root'

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

def table_name(obj):
    return 'T' + str(id(obj))

# TODO: cleaner format. Rather than nesting tables, use a foreign key setup to link to conceptually "nested" tables.
Eqn = namedtuple('Equation', ['lhs', 'rhs'])
class Solver(TreeWalk):
    def solve_symbol(self, eqn):
        return {eqn.lhs: eqn.rhs}
    
    def solve_transform(self, eqn, solve):
        # We have f(x) = rhs, so to solve it, we solve x = inv(rhs)
        return solve(Eqn(eqn.lhs.x, eqn.lhs.inv(eqn.rhs)))
    
    def solve_dict(self, eqn, solve):
        # NOTE: need to handle same-symbol conflicts
        # TODO: type check RHS
        solution = {}
        for k, v in eqn.lhs.items():
            # TODO: implement Nullable and handle missing stuff in general
            solution.update(solve(Eqn(v, eqn.rhs.get(k, None))))
        return solution
    
    def solve_list(self, eqn, solve):
        # TODO: type check RHS & handle single item
        
        parent_table = self.current_table
        parent_row = len(self.tables[self.current_table])
        
        # TODO: handle initialization in a separate walk
        for lhs in eqn.lhs:
            table = table_name(lhs)
            if not table in self.tables:
                self.tables[table] = pd.DataFrame()
        
        # Each entry of eqn.lhs is actually independent, but we only want to walk
        # eqn.rhs once (to handle streams), so we handle all the eqn.lhs entries
        # inside of the eqn.rhs loop.
        solutions = [[] for lhs in eqn.lhs]
        for rhs in eqn.rhs:
            for ind, lhs in enumerate(eqn.lhs):
                self.current_table = table_name(lhs)
                try:
                    solution = solve(Eqn(lhs, rhs))
                    solutions[ind].append(solution)
                    
                    solution[parent_table] = parent_row
                    self.tables[self.current_table] = self.tables[self.current_table].append(solution, ignore_index=True)
                except NoMatchException:
                    # This is the filter functionality
                    continue
        self.current_table = parent_table
        
        for ind, subsolutions in enumerate(solutions):
            if not subsolutions:
                raise NoMatchException('No match found for:', eqn.lhs[ind])
        # NOTE: using id on rhs would be Bad, because streams, but lhs is fine.
        return {} #{InternalSymbol(id(lhs)): pd.DataFrame(solutions[ind]) for ind, lhs in enumerate(eqn.lhs)}
    
    def check_match(self, eqn):
        if eqn.lhs != eqn.rhs:
            raise NoMatchException('LHS does not match data:', eqn.lhs)
        return {}
        
    def __init__(self):
        super().__init__([
            (lambda eqn: isinstance(eqn.lhs, S), self.solve_symbol),
            (lambda eqn: isinstance(eqn.lhs, Transform), self.solve_transform),
            (lambda eqn: isinstance(eqn.lhs, dict), self.solve_dict),
            (lambda eqn: isinstance(eqn.lhs, list), self.solve_list),
            (lambda eqn: True, self.check_match)])
    
    def __call__(self, tree):
        self.current_table = root
        self.tables = {root: pd.DataFrame()}
        super().__call__(tree)
        
        # Outermost elements need a parent to point to, so we use a singleton self-pointer
        self.tables[root] = self.tables[root].append({root: 0}, ignore_index=True)
        return self.tables
        
solver = Solver()


data = [{'name': 'john', 'addresses': [{'state': 'CA'}, {'state': 'CT'}], 'houses':[{'state': 'CT'}]},
        {'name': 'allan', 'addresses': [{'state': 'CA'}, {'state': 'WA'}], 'houses':[{'state': 'WA'}]}]
match_template = [{'name': S('name'), 'addresses': [{'state': S('state')}], 'houses':[{'state': S('state')}]}]
