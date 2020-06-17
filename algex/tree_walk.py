from collections import OrderedDict

class TreeWalk:
    def __init__(self, cases):
        self.cases = OrderedDict(cases)
    
    def walk(self, tree):
        for condition, rule in self.cases.items():
            if condition(tree):
                return rule(tree, self.walk)
        return tree  # If you want a particular default, then make a catch-all case
    
    def __call__(self, tree):
        return self.walk(tree)
