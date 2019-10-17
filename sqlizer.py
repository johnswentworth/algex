from symbol import BaseSymbol, S, InternalSymbol
from transform import Transform
from solver2 import Solver, Eqn, pd, root

from sqlalchemy.ext.automap import automap_base
from sqlalchemy import create_engine
engine = create_engine('sqlite:///:memory:')

data = [{'name': 'john', 'addresses': [{'state': 'CA'}, {'state': 'CT'}], 'houses':[{'state': 'CT'}]},
        {'name': 'allan', 'addresses': [{'state': 'CA'}, {'state': 'WA'}], 'houses':[{'state': 'WA'}]}]
match_template = [{'name': S('name'), 'addresses': [{'state': S('state')}], 'houses':[{'state': S('state')}]}]

solver = Solver()
tables = solver(Eqn(match_template, data))

# post-processing on tables
for tablename, table in tables.items():
    if tablename == root:
        table.to_sql(name=tablename, con=engine)
        continue
    
    # for joining based on matching column names, make sure index becomes a column with same name as table
    table.to_sql(name=tablename, con=engine, index=True, index_label=tablename)

Base = automap_base()
Base.prepare(engine, reflect=True)
table_classes = Base.classes

# TODO: I think I need to just bite the bullet and generate model classes from the template
