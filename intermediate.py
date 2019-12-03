from functools import reduce
import pandas as pd

from symbol import S, InternalSymbol
from sqlizer import get_tree_structure, get_symbol_directory, root #, build_schema

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


data = [{'name': 'john', 'addresses': [{'state': 'CA'}, {'state': 'CT'}], 'houses':[{'state': 'CT'}]},
        {'name': 'allan', 'addresses': [{'state': 'CA'}, {'state': 'WA'}], 'houses':[{'state': 'WA'}]}]
match_template = [{'name': S('name'), 'addresses': [{'state': S('state')}], 'houses':[{'state': S('state')}]}]

class Everything:
    # Fuck you Russell
    def __contains__(self, item):
        return True
everything  = Everything()


class Intermediate:
    def build(self, lhs):
        return  # By default, build step does nothing
    
    def append(self, table, row):
        pass  # Main method which needs to be overridden for solve
    
    def finish(self):
        pass # Any postprocessing needed before queries are run goes here
    
    def size(self, table):
        pass  # Only query which needs to work *before* calling finish()
    
    def query(self, query):
        pass  # Main method which needs to be overridden for substitute

class Canonicalizer(dict):
    # Used to translate between Symbols/symbol strings and their corresponding columns in SQLIntermediates
    def __init__(self, model_classes):
        self.canonicalizer = {}
        for model in model_classes.values():
            for column_name, column in model.__table__.columns.items():
                self.canonicalizer.setdefault(column_name, []).append(model)
        return super().__init__(self.canonicalizer)
    
    def get_canonical_column(self, symbol):
        # grab canonical model from canonicalizer[sym][0]
        # then get the appropriate sqlalchemy col from that model from .__dict__[sym]
        if isinstance(symbol, S):
            return self.canonicalizer[symbol.s][0].__dict__[symbol.s]
        return self.canonicalizer[symbol][0].__dict__[symbol]
    
    def get_constraints(self):
        # Whenever two column names match, add a SQL constraint that their values must match
        constraints = []
        for column_name, models in self.canonicalizer.items():
            if len(models) <= 1:
                continue
            for model in models[1:]:
                # TODO: I'm using __dict__ because I'm not sure how to get class attributes
                constraints.append(models[0].__dict__[column_name] == model.__dict__[column_name])
        return constraints

class SQLIntermediate(Intermediate):
    def __init__(self, types={}, engine=None):
        self.Base = declarative_base()
        self.types = types
        
        if engine is None:
            engine = create_engine('sqlite:///:memory:')
        self.engine = engine
    
    def build(self, lhs):
        # TODO: either taskify or memoize so we don't repeat work when subclasses need metadata first
        self.symbol_directory = get_symbol_directory(lhs)
        self.parents = get_tree_structure(lhs)
        
        self.model_classes = self.build_schema()
        self.Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # We need counts all the time while solving, so keep them python-side
        self.counts = {table: 0 for table in self.model_classes}
        
        self.canonicalizer = Canonicalizer(self.model_classes)
        self.constraints = self.canonicalizer.get_constraints()
    
    def build_schema(self):
        # Create sqlalchemy model classes for each table
        model_classes = {}
        for table in self.parents:
            parent = self.parents[table]
            attrs = {'__tablename__': table.s, 
                     table.s: Column(Integer, primary_key=True), # TODO: do we need to specify autoincrement?
                     parent.s: Column(Integer, ForeignKey(parent.s + '.' + parent.s))}
            
            attrs.update({symbol.s: Column(self.types[symbol], nullable=True, index=True) for symbol in self.symbol_directory[table]})
            model = type(table.s, (self.Base,), attrs)  # This is how you create a class on-the-fly in Python
            model_classes[table] = model
        model_classes[root] = type(root.s, (self.Base,), {'__tablename__': root.s, 
                     root.s: Column(Integer, primary_key=True)})
        return model_classes
    
    def append(self, table, row):
        model = self.model_classes[table]
        self.session.add(model(**{k.s: v for k, v in row.items()}))
        self.counts[table] += 1
    
    def finish(self):
        model = self.model_classes[root]
        self.session.add(model(**{root.s: 1}))  # TODO: for some reason autoincrement starts at 1???
        self.session.commit()
    
    def size(self, table):
        return self.counts[table]
    
    def show(self):
        db = {tb_name: self.session.query(tb).all() for tb_name, tb in self.model_classes.items()}
        return {tb_name: [obj.__dict__ for obj in tb] for tb_name, tb in db.items()}
    
    def query(self, symbols=everything, known_values={}):
        if symbols is everything:
            symbols = [S(symbol_name) for symbol_name in self.canonicalizer]
        
        known_value_constraints = [(self.canonicalizer.get_canonical_column(sym) == val) for sym, val in known_values.items()]
        query_cols = [self.canonicalizer.get_canonical_column(sym) for sym in symbols]
        
        for result in self.session.query(*query_cols).\
            filter(*self.constraints).\
            filter(*known_value_constraints).\
            distinct().all():
            yield {sym: res for sym, res in zip(symbols, result)}
        return

class MemoryIntermediate(SQLIntermediate):
    # Uses an in-memory sqlite db and assigns id's to store in db, so non-serializable objects can be used in data
    # NOTE: data for any repeated symbols must be hashable
    def __init__(self, types={}):
        self.direct_types = types
        self.decoder = []
        self.encoder = {0:0}
        super().__init__(types=types)
    
    def build(self, lhs):
        self.symbol_directory = get_symbol_directory(lhs)
        all_symbols = reduce(set.union, self.symbol_directory.values(), set())
        # TODO: interaction between this and base class build is confusing
        self.types = {s:self.direct_types.get(s, Integer) for s in all_symbols}
        super().build(lhs)
    
    def append(self, table, row):
        encoded_row = {}
        for k, v in row.items():
            if k in self.direct_types:
                encoded_row[k] = v
                continue
            
            if isinstance(k, InternalSymbol):
                # These are all autoincrement, so don't encode them
                encoded_row[k] = v + 1 # NOTE: for some reason autoincrement is starting at 1???
                continue
            
            if len(self.canonicalizer[k.s]) > 1 and v in self.encoder:
                encoded_row[k] = self.encoder[v]
                continue
            
            encoded_row[k] = len(self.decoder)
            self.encoder[v] = len(self.decoder)
            self.decoder.append(v)
        
        super().append(table, encoded_row)
    
    def query(self, symbols=everything, known_values={}):
        # TODO: don't encode/decode InternalSymbols
        known_values = {sym: self.encoder[val] for sym, val in known_values.items()}
        for encoded_result in super().query(symbols=symbols, known_values=known_values):
            yield {sym: self.decoder[res] for sym, res in encoded_result.items()}
        return

class PandasIntermediate(Intermediate):
    def build(self, lhs):
        parents = get_tree_structure(lhs)
        self.solutions = {table: pd.DataFrame() for table in parents}
        self.solutions[root] = pd.DataFrame()
    
    def append(self, table, row):
        self.solutions[table] = self.solutions[table].append(row, ignore_index=True)
    
    def finish(self):
        # Outermost elements need a parent to point to, so we use a singleton self-pointer
        self.solutions[root] = self.solutions[root].append({root: 0}, ignore_index=True)
    
    def size(self, table):
        return len(self.solutions[table])
