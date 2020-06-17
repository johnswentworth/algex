from .symbol import S
from .transform import Transform
from .error_handler import ErrorHandler

from .solver import solver, Eqn
from .intermediate import PandasIntermediate, MemoryIntermediate, Intermediate
from .sqlizer import update

from .tree_walk import TreeWalk
from functools import reduce
from itertools import chain
from collections import namedtuple

# Test data
data = [{'name': 'john', 'addresses': [{'state': 'CA'}, {'state': 'CT'}], 'houses':[{'state': 'CT'}]},
        {'name': 'allan', 'addresses': [{'state': 'CA'}, {'state': 'WA'}], 'houses':[{'state': 'WA'}]}]
match_template = [{'name': S('name'), 'addresses': [{'state': S('state')}], 'houses':[{'state': S('state')}]}]

#intermediate = MemoryIntermediate()
#soln = solver(Eqn(match_template, data), intermediate)

get_outer_symbols = TreeWalk([
        (lambda tree: isinstance(tree, S), lambda tree, walk: [tree]),
        (lambda tree: isinstance(tree, Transform), lambda tree, walk: walk(tree.x)),
        (lambda tree: isinstance(tree, dict), lambda tree, walk: reduce(list.__add__, [walk(v) for v in tree.values()])),
        (lambda tree: True, lambda tree, walk: [])])

dispatch_cache = {}
Substitution = namedtuple('Substitution', ['expr', 'solutions', 'known_values'])
class Assigner(TreeWalk):
    def __init__(self):
        super().__init__([
        (lambda tree: isinstance(tree.expr, S), lambda tree, walk: tree.known_values[tree.expr]),
        (lambda tree: isinstance(tree.expr, Transform), lambda tree, walk: tree.expr.f(walk(Substitution(tree.expr.x, tree.solutions, tree.known_values)))),
        (lambda tree: isinstance(tree.expr, ErrorHandler), lambda tree, walk: walk(Substitution(tree.expr.x, tree.solutions, tree.known_values))),
        (lambda tree: isinstance(tree.expr, dict), lambda tree, walk: {k: walk(Substitution(v, tree.solutions, tree.known_values)) for k, v in tree.expr.items()}),
        # NOTE: next line is the one to change if we want results to contain iterators instead of lists.
        (lambda tree: isinstance(tree.expr, list), lambda tree, walk: list(chain(*[substitute(subtree, tree.solutions, tree.known_values) for subtree in tree.expr]))),
        (lambda tree: True, lambda tree, walk: tree.expr)])
    
    def walk(self, tree):
        tp = type(tree.expr)
        if tp in dispatch_cache:
            return dispatch_cache[tp](tree, self.walk)
        
        for condition, rule in self.cases.items():
            if condition(tree):
                dispatch_cache[tp] = rule
                return rule(tree, self.walk)
        return tree
assigner = Assigner()

def assign(template, solution, known_values):
    return assigner(Substitution(template, solution, known_values))

def substitute_list(template, solutions, known_values={}):
    for soln in solutions:
        yield assign(template, [soln], update(known_values, soln))
    return

def substitute_intermediate(template, intermediate, known_values={}):
    # Collect all symbols outside of lists (outer symbols)
    outer_symbols = get_outer_symbols(template)
    #outer_symbols.append(InternalSymbol('root'))  # Avoids empty queries
    
    # for each value of the outer symbols...
    for soln in intermediate.query(outer_symbols, known_values):
        # recursively substitute into each list-template with the known values as constraints
        yield assign(template, intermediate, update(known_values, soln))
    return

def substitute(template, solution, known_values={}):
    '''solution can be:
        - a dict: will substitute that one solution into template
        - an iterable of dicts: will return an iterable, with each result corresponding to one solution
        - an Intermediate (returned by solve()): same as iterable, but often achieves better big-O efficiency via lazy access'''
    
    # TODO: we currently distinct all results, so multiplicity is not supported
    # To allow multiplicity, we need to be clever about our SQL - we need multiplicity
    # defined by the symbols SELECTed, but NOT symbols in constraints
    # For instance, right now if we just query S('root') w/o distinct, we get back
    # one result for each soln of the full eqn, even though root has only one value
    # in the db.
    
    
    if isinstance(solution, Intermediate):
        result = substitute_intermediate(template, solution, known_values)
        return result
    if isinstance(solution, dict):
        return assign(template, solution, update(known_values, solution))
    
    return substitute_list(template, solution, known_values)
