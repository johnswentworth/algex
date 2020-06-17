from functools import reduce

from .symbol import S, InternalSymbol
from .sqlizer import get_tree_structure, get_symbol_directory, root #, build_schema

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
    
    def __iter__(self):
        # Method to iterate through ALL solutions. Note that there may be exponentially many!
        # Should not include InternalSymbols
        pass
    
    def query(self, symbols=everything, known_values={}):
        pass  # Main method which needs to be overridden for substitute

class Canonicalizer(dict):
    # Used to translate between Symbols/symbol strings and their corresponding columns in SQLIntermediates
    def __init__(self, model_classes):
        self.canonicalizer = {}
        for model in model_classes.values():
            for column_name, column in model.__table__.columns.items():
                if column_name in {'_id', '_parent_id'}:
                    # tree bookkeeping symbol
                    continue
                self.canonicalizer.setdefault(column_name, []).append(model)
        return super().__init__(self.canonicalizer)
    
    def get_canonical_column(self, symbol):
        # grab canonical model from canonicalizer[sym][0]
        # then get the appropriate sqlalchemy col from that model from .__dict__[sym]
        if isinstance(symbol, S):
            return self.canonicalizer[symbol.s][0].__dict__[symbol.s]
        return self.canonicalizer[symbol][0].__dict__[symbol]
    
    def get_non_tree_constraints(self):
        # Whenever two column names match, add a SQL constraint that their values must match
        non_tree_constraints = []
        repeated_symbols = []
        for column_name, models in self.canonicalizer.items():
            if len(models) <= 1:
                continue
            repeated_symbols.append(S(column_name))
            for model in models[1:]:
                # TODO: I'm using __dict__ because I'm not sure how to get class attributes
                non_tree_constraints.append(models[0].__dict__[column_name] == model.__dict__[column_name])
        return non_tree_constraints, repeated_symbols

class SQLIntermediate(Intermediate):
    def __init__(self, types={}, engine=None):
        self.Base = declarative_base()
        self.types = types
        
        if engine is None:
            engine = create_engine('sqlite:///:memory:')
        self.engine = engine
    
    def build(self, lhs):
        # TODO: either taskify or memoize so we don't repeat work when subclasses need metadata first
        try:
            self.symbol_directory  # Check if subclass already computed directory
        except:
            self.symbol_directory = get_symbol_directory(lhs) # list symbols in each table
        
        self.reverse_symbol_directory = {} # list tables containing each symbol
        for table_sym in self.symbol_directory:
            for sym in self.symbol_directory[table_sym]:
                self.reverse_symbol_directory.setdefault(sym, []).append(table_sym)
        self.parents = get_tree_structure(lhs)
        
        self.model_classes = self.build_schema()
        self.Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # Fake it until we make it
        self.cache = {table: [] for table in self.model_classes}
        # We need counts all the time while solving, so keep them python-side
        self.counts = {table: 0 for table in self.model_classes}
        
        self.canonicalizer = Canonicalizer(self.model_classes)
        self.non_tree_constraints, self.repeated_symbols = self.canonicalizer.get_non_tree_constraints()
    
    def build_schema(self):
        # Create sqlalchemy model classes for each table
        model_classes = {}
        for table in self.parents:
            parent = self.parents[table]
            attrs = {'__tablename__': table.s, 
                     '_id': Column(Integer, primary_key=True),
                     '_parent_id': Column(Integer, ForeignKey(parent.s + '._id'))}
            
            attrs.update({symbol.s: Column(self.types[symbol], nullable=True, index=True) for symbol in self.symbol_directory[table]})
            model = type(table.s, (self.Base,), attrs)  # This is how you create a class on-the-fly in Python
            model_classes[table] = model
        model_classes[root] = type(root.s, (self.Base,), {'__tablename__': root.s, 
                     '_id': Column(Integer, primary_key=True)})
        return model_classes
    
    def append(self, table, row):
        self.cache[table].append(row)
        self.counts[table] += 1
    
    def finish(self):
        model = self.model_classes[root]
        self.session.add(model(**{'_id': 1}))  # TODO: for some reason autoincrement starts at 1???
        for table, rows in self.cache.items():
            # TODO: do we need to insert objects to parent tables before child tables?
            model = self.model_classes[table]
            self.session.bulk_save_objects([model(**{k.s: v for k, v in row.items()}) for row in rows])
        self.session.commit()
    
    def size(self, table):
        return self.counts[table]
    
    def __iter__(self):
        all_symbols = reduce(set.union, self.symbol_directory.values())
        return self.query([sym for sym in all_symbols if not isinstance(sym, InternalSymbol)])
    
    def get_single(self):
        # TODO: efficient get_single()
        return [s for s in self][0]
    
    def show(self):
        db = {tb_name: self.session.query(tb).all() for tb_name, tb in self.model_classes.items()}
        return {tb_name: [obj.__dict__ for obj in tb] for tb_name, tb in db.items()}
    
    def get_relevant_tables(self, relevant_symbols):
        # TODO: would be great if this function didn't even need to exist.
        directly_relevant_tables = list(set(sum((self.reverse_symbol_directory[sym] for sym in relevant_symbols), [])))
        
        # A little involved, because order matters - want parents to appear before their children
        redundant_relevant_tables = []
        for table_sym in directly_relevant_tables:
            while table_sym != S('root'):
                redundant_relevant_tables.append(table_sym)
                table_sym = self.parents[table_sym]
        #redundant_relevant_tables.append(S('root'))
        
        redundant_relevant_tables.reverse()
        relevant_tables = []
        relevant_tables_used = set()
        for t in redundant_relevant_tables:
            if t not in relevant_tables_used:
                relevant_tables.append(t)
                relevant_tables_used.add(t)
        return relevant_tables
    
    def query(self, symbols=everything, known_values={}):
        if symbols is everything:
            symbols = [S(symbol_name) for symbol_name in self.canonicalizer]
        
        known_value_constraints = [(self.canonicalizer.get_canonical_column(sym) == val) for sym, val in known_values.items()]
        query_cols = [self.canonicalizer.get_canonical_column(sym) for sym in symbols]
        
        # one hacky but important query optimization: identify all variables with tree-violating contraints,
        # and include them in all queries. Other than that, only include contraints needed for tree.
        relevant_symbols = list(set(symbols + list(known_values.keys()) + self.repeated_symbols))
        relevant_tables = self.get_relevant_tables(relevant_symbols)
        
        #print(self.show())
        
        # TODO: clean up query construction and related cruft
        query = self.session.query(self.model_classes[root], *query_cols)
        for table in relevant_tables:
            query = query.join(self.model_classes[table],
                               self.model_classes[table]._parent_id == self.model_classes[self.parents[table]]._id)
        query = query.\
            filter(*known_value_constraints).\
            filter(*self.non_tree_constraints).\
            distinct()
        #print(str(query))
        for result in query.all():
            if len(symbols) == 0:
                # check that a solution exists, then yield empty.
                # needs a special case because result is just the root object in this case, rather than a tuple with root as first element
                yield {}
                return
            yield {sym: res for sym, res in zip(symbols, result[1:])}
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
    
    def encode(self, symbol, value):
        if symbol in self.direct_types:
            return value
        if isinstance(symbol, InternalSymbol):
            return value + 1 # NOTE: for some reason autoincrement is starting at 1?
        if value in self.encoder:
            return self.encoder[value]
        
        self.encoder[value] = len(self.decoder)
        self.decoder.append(value)
        return len(self.decoder) - 1
    
    def decode(self, symbol, value):
        if symbol in self.direct_types:
            return value
        if isinstance(symbol, InternalSymbol):
            return value - 1
        return self.decoder[value]
    
    def append(self, table, row):
        encoded_row = {k: self.encode(k, v) for k, v in row.items()}
        super().append(table, encoded_row)
    
    def query(self, symbols=everything, known_values={}):
        known_values = {sym: self.encode(sym, val) for sym, val in known_values.items()}
        for encoded_result in super().query(symbols=symbols, known_values=known_values):
            yield {sym: self.decode(sym, res) for sym, res in encoded_result.items()}
        return

class PandasIntermediate(Intermediate):
    # Mainly useful for testing the solver.
    def build(self, lhs):
        import pandas as pd  # Huge library, don't want to require it
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
