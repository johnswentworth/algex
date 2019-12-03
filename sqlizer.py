from functools import reduce

from symbol import S
from transform import Transform
from misc import table_name, root
from tree_walk import TreeWalk

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, ForeignKey

# Test data
data = [{'name': 'john', 'addresses': [{'state': 'CA'}, {'state': 'CT'}], 'houses':[{'state': 'CT'}]},
        {'name': 'allan', 'addresses': [{'state': 'CA'}, {'state': 'WA'}], 'houses':[{'state': 'WA'}]}]
match_template = [{'name': S('name'), 'addresses': [{'state': S('state')}], 'houses':[{'state': S('state')}]}]

def update(d1, d2):
    result = {}
    result.update(d1)
    result.update(d2)
    return result

def get_tree_structure(lhs):
    # Map each child to its parent
    
    # We'll first extract the relevant structure as a tree, then flatten and invert
    walker = TreeWalk([
        (lambda lhs: isinstance(lhs, Transform), lambda tree, walk: walk(tree.x)),
        (lambda lhs: isinstance(lhs, dict), lambda tree, walk: reduce(update, [walk(v) for v in tree.values()], {})),
        (lambda lhs: isinstance(lhs, list), lambda tree, walk: {table_name(item): walk(item) for item in tree}),
        (lambda lhs: True, lambda tree: {})])
    structure = {root: walker(lhs)}
    
    def invert_and_flatten(tree):
        result = {}
        for k, v in tree.items():
            result.update({i: k for i in v})
            result.update(invert_and_flatten(v))
        return result
    
    return invert_and_flatten(structure)

def get_symbol_directory(lhs):
    # Extract a dict mapping "tables" to the symbols they contain
    # Note: this assumes top-level is a list
    directory = {}
    
    def handle_list(tree, walk):
        for item in tree:
            directory[table_name(item)] = walk(item)
        return set()
    
    walker = TreeWalk([
        (lambda lhs: isinstance(lhs, S), lambda tree: {tree}),
        (lambda lhs: isinstance(lhs, Transform), lambda tree, walk: walk(tree.x)),
        (lambda lhs: isinstance(lhs, dict), lambda tree, walk: reduce(set.union, map(walk, tree.values()))),
        (lambda lhs: isinstance(lhs, list), handle_list),
        (lambda lhs: True, lambda tree: set())])
    directory[root] = walker(lhs)
    return directory
