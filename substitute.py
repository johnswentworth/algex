from symbol import S, InternalSymbol
from transform import Transform

from solver import solver, Eqn
from intermediate import PandasIntermediate, MemoryIntermediate
from sqlizer import get_tree_structure, get_symbol_directory, update

from tree_walk import TreeWalk
from functools import reduce
from itertools import chain

# Test data
data = [{'name': 'john', 'addresses': [{'state': 'CA'}, {'state': 'CT'}], 'houses':[{'state': 'CT'}]},
        {'name': 'allan', 'addresses': [{'state': 'CA'}, {'state': 'WA'}], 'houses':[{'state': 'WA'}]}]
match_template = [{'name': S('name'), 'addresses': [{'state': S('state')}], 'houses':[{'state': S('state')}]}]

intermediate = MemoryIntermediate()
soln = solver(Eqn(match_template, data), intermediate)

get_outer_symbols = TreeWalk([
        (lambda tree: isinstance(tree, S), lambda tree: [tree]),
        (lambda tree: isinstance(tree, Transform), lambda tree, walk: walk(tree.x)),
        (lambda tree: isinstance(tree, dict), lambda tree, walk: reduce(list.__add__, [walk(v) for v in tree.values()])),
        (lambda tree: True, lambda tree: [])])

def assign(template, solution, known_values):
    walker = TreeWalk([
        (lambda tree: isinstance(tree, S), lambda tree: known_values[tree]),
        (lambda tree: isinstance(tree, Transform), lambda tree, walk: tree.f(walk(tree.x))),
        (lambda tree: isinstance(tree, dict), lambda tree, walk: {k: walk(v) for k, v in tree.items()}),
        # NOTE: next line is the one to change if we want results to contain iterators instead of lists.
        (lambda tree: isinstance(tree, list), lambda tree, walk: list(chain(*[substitute(subtree, solution, known_values) for subtree in tree]))),
        (lambda tree: True, lambda tree: tree)])
    return walker(template)

def substitute(template, solution, known_values={}):
    # Collect all symbols outside of lists (outer symbols)
    outer_symbols = get_outer_symbols(template)
    outer_symbols.append(InternalSymbol('root'))  # Avoids empty queries
    
    # TODO: we currently distinct all results, so multiplicity is not supported
    # To allow multiplicity, we need to be clever about our SQL - we need multiplicity
    # defined by the symbols SELECTed, but NOT symbols in constraints
    # For instance, right now if we just query S('root') w/o distinct, we get back
    # one result for each soln of the full eqn, even though root has only one value
    # in the db.
    
    # for each value of the outer symbols...
    for soln in solution.query(outer_symbols, known_values):
        # recursively substitute into each list-template with the known values as constraints
        yield assign(template, solution, update(known_values, soln))
    return
