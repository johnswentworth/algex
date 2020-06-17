from symbol import S, InternalSymbol
from transform import Transform
from error_handler import ErrorHandler
from tree_walk import TreeWalk
from misc import root, NoMatchException, table_name

from collections import namedtuple

try:
    import pandas as pd
except ModuleNotFoundError as e:
    # TODO: fallback
    raise e

# TODO: cleaner format. Rather than nesting tables, use a foreign key setup to link to conceptually "nested" tables.
Eqn = namedtuple('Equation', ['lhs', 'rhs'])
dispatch_cache = {}
class Solver(TreeWalk):
    def solve_symbol(self, eqn, solve):
        return {eqn.lhs: eqn.rhs}
    
    def solve_transform(self, eqn, solve):
        # We have f(x) = rhs, so to solve it, we solve x = inv(rhs)
        return solve(Eqn(eqn.lhs.x, eqn.lhs.inv(eqn.rhs)))
    
    def solve_error_handler(self, eqn, solve):
        try:
            return solve(Eqn(eqn.lhs.x, eqn.rhs))
        except Exception as e:
            return eqn.lhs.handle_error(e, self.intermediate, self.current_table, eqn.rhs)
    
    def solve_dict(self, eqn, solve):
        # NOTE: need to handle same-symbol conflicts
        # TODO: type check RHS
        solution = {}
        for k, v in eqn.lhs.items():
            solution.update(solve(Eqn(v, eqn.rhs.get(k, None))))
        return solution
    
    def solve_list(self, eqn, solve):
        # TODO: type check RHS & handle single item
        
        parent_table = self.current_table
        parent_row = self.intermediate.size(parent_table)
        
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
                    
                    #solution[parent_table] = parent_row
                    solution[InternalSymbol('_parent_id')] = parent_row
                    self.intermediate.append(self.current_table, solution)
                    #self.tables[self.current_table] = self.tables[self.current_table].append(solution, ignore_index=True)
                except NoMatchException:
                    # This is the filter functionality
                    continue
        self.current_table = parent_table
        
        for ind, subsolutions in enumerate(solutions):
            if not subsolutions:
                raise NoMatchException('No match found for:', eqn.lhs[ind])
        return {}
    
    def check_match(self, eqn, solve):
        if eqn.lhs != eqn.rhs:
            raise NoMatchException('LHS does not match data:', eqn.lhs)
        return {}
        
    def __init__(self):
        super().__init__([
            (lambda eqn: isinstance(eqn.lhs, S), self.solve_symbol),
            (lambda eqn: isinstance(eqn.lhs, Transform), self.solve_transform),
            (lambda eqn: isinstance(eqn.lhs, ErrorHandler), self.solve_error_handler),
            (lambda eqn: isinstance(eqn.lhs, dict), self.solve_dict),
            (lambda eqn: isinstance(eqn.lhs, list), self.solve_list),
            (lambda eqn: True, self.check_match)])
    
    def walk(self, tree):
        tp = type(tree.lhs)
        if tp in dispatch_cache:
            return dispatch_cache[tp](tree, self.walk)
        
        for condition, rule in self.cases.items():
            if condition(tree):
                dispatch_cache[tp] = rule
                return rule(tree, self.walk)
        return tree
    
    def __call__(self, eqn, intermediate):
        self.intermediate = intermediate
        intermediate.build(eqn.lhs)
        
        self.current_table = root
        super().__call__(eqn)
        
        intermediate.finish()
        return intermediate
        
solver = Solver()
    

data = [{'name': 'john', 'addresses': [{'state': 'CA'}, {'state': 'CT'}], 'houses':[{'state': 'CT'}]},
        {'name': 'allan', 'addresses': [{'state': 'CA'}, {'state': 'WA'}], 'houses':[{'state': 'WA'}]}]
match_template = [{'name': S('name'), 'addresses': [{'state': S('state')}], 'houses':[{'state': S('state')}]}]

'''
from intermediate import PandasIntermediate, MemoryIntermediate
intermediate = MemoryIntermediate()
soln = solver(Eqn(match_template, data), intermediate)
'''
