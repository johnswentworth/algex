from inspect import signature
from collections import OrderedDict

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
