# High-School Algebra for Data Structures
A surprising amount of day-to-day software engineering can be expressed as solving equations like:
```python
{                                   {
    "person": {                         "person": {
        "first_name": x,      =             "first_name": "Alice",
        "last_name": y                      "last_name": "Liddell"
    }                                   }
}                                   }
```
… finding the solution `(x = “Alice”, y = “Liddell”)`, and then substituting that solution into some other expression.

This is primarily useful for transforming data from one format to another. Typical use-cases include collecting data from an external API and transforming it into the schema used in our database, or transforming data from one API into the format needed by another API. Typically, these sort of tasks are conceptually simple, but they get very tedious and messy when mapping a large number of fields between deeply-nested data formats. Personally, I worked out these ideas while at [LoanSnap](https://www.goloansnap.com/), a mortgage startup needing to map thousands of fields between dozens of different data formats; you can imagine how messy that would get.

Why write transformations as equations, rather than writing out `x = data["person"]["firstName"]; y = data["person"]["lastName"]; …`? A few advantages:
 - When we write data transformations as equations, the structure of our code matches the structure of our data - indeed, our “code” is essentially a template whose structure matches the data. We'll see examples below. This makes the code much more readable and maintainable when dealing with large, deeply-nested data structures.
 - This is a declarative (rather than imperative) method for specifying data transformations, so it comes with the usual benefits of declarativity. In particular, a library for solving data-structure-equations can handle missing data and other errors in standard ways without having to hand-code checks for every single field - especially useful when entire nested structures can be missing. See the Nullable examples below.
 - Because the “code” defining a transformation is itself a data structure, we can potentially track/visualize/audit data flow without having to track arbitrary code.

## Basic Example
Let's walk through our Alice problem from earlier. We want to solve
```python
{                                   {
    "person": {                         "person": {
        "first_name": x,      =             "first_name": "Alice",
        "last_name": y                      "last_name": "Liddell"
    }                                   }
}                                   }
```
... and find the solution `(x = “Alice”, y = “Liddell”)`.

Using the algex library, we can set up the problem like this:
```python
from algex import S, solve, substitute

data = {
	"person": {
		"first_name": "Alice",
		"last_name": "Liddell",
		"other_info": ["..."]
	}
}

template = {
    "person": {
	    "first_name": S("x"),
	    "last_name": S("y")
	}
}

solutions = solve(template, data)
```
Here `S` stands for Symbol - i.e. a variable to solve for. We can read out the solutions by iterating:
```python
>>> list(solutions)
[{S('x'): 'Alice', S('y'): 'Liddell'}]
```
As expected, we have exactly one solution: `(x= "Alice", y="Liddell")`.

In practice, we usually don't just want to read off the solutions; we want to substitute them into some other template. Continuing our previous example:
```python
>>> output_template = {
	"name": S("x"),
	"details": {
		"last_name": S("y")
	}
}
>>> list(substitute(output_template, solutions))
[{'name': 'Alice', 'details': {'last_name': 'Liddell'}}]
```
Notice that we cast the results of both `solve()` and `substitute()` to lists; by default they are generators. That's because, depending on the output template, we might not need to enumerate all the possible solutions. `solve()` yields a lazy representation of the solutions, and `substitute()` accesses only what it needs. This is important when we have a large number of solutions, but our input and output formats use a compressed representation.

## Multiple Solutions and Lists
The algex library interprets lists as multiple solutions. A simple example:
```python
>>> template = [S("x")]
>>> data = [1, 2, 3]
>>> list(solve(template, data))
[{S('x'): 1}, {S('x'): 2}, {S('x'): 3}]
```
Our equation is `[x] = [1, 2, 3]`, and we see three solutions: `x = 1`, `x = 2`, and `x = 3`.

This convention turns out to produce the behavior we usually want in day-to-day data-munging.

An example: we have a list of people, each of which has a list of addresses. We want to "transpose" this data: produce a list of states, each of which has a list of people with an address in that state. Data and templates:
```python
data = [{"name": "john", "addresses": [
 			{"state": "CA"},
 			{"state": "CT"}]},
 		{"name": "allan", "addresses": [
 			{"state": "CA"},
 			{"state": "WA"}]
}]

input_template = [{
	"name": S("name"),
	"addresses": [{
		"state": S("state")
	}]
}]

output_template = [{
	"state": S("state"),
	"names": [S("name")]
}]
```
We solve and substitute:
```python
>>> solutions = solve(input_template, data)
>>> list(substitute(output_template, solutions))
[[{'state': 'CA', 'names': ['john', 'allan']},
  {'state': 'CT', 'names': ['john']},
  {'state': 'WA', 'names': ['allan']}]]
```
Notice that our equation has four solutions: `(name="john", state="CA")`, `(name="john", state="CT")`, `(name="allan", state="CA")`, and `(name="allan", state="WA")`. However, we never explicitly compute the four solutions. The `solve()` method returns a lazy data structure, and then the `substitute()` method looks up information as-needed.

An example from the tests shows why efficient representations matter:
```python
data = {'u':[random.random() for i in range(1000)],
        'v':[random.random() for i in range(1000)],
        'w':[random.random() for i in range(1000)],
        'x':[random.random() for i in range(1000)],
        'y':[random.random() for i in range(1000)],
        'z':[random.random() for i in range(1000)]}
template = {'u':[S('u')], 'v':[S('v')], 'w':[S('w')], 'x':[S('x')], 'y':[S('y')], 'z':[S('z')]}

# Should take several decades if solutions are fully enumerated
m = solve(template, data) 
result = list(substitute(template, m))
```
In this case, there are 1000^6 possible solutions - all combinations of one thousand solutions for each of six variables. But we don't actually need to enumerate all combinations in order to compute the final result; in this case we just need the solutions for each variable independently. (Of course, we *could* write an output template which needs all combinations - e.g. `[{'u': S('u'), 'v': S('v'), ...}]`. In practice, you probably don't want that.)

Note that, in full generality, equation-solving is NP-complete. A good heuristic is that the algex library will be efficient in a big-O sense for the same problems on which a SQL query would be efficient (assuming all the necessary indices are present). Indeed, the algex library uses a SQL database under the hood.

## Transformations
Of course data-munging involves all sorts of little transformations on individual fields - e.g. parsing/formatting strings, changing datetime formats, etc. These are just general transformations, and they work the same way they work in math class. We have an equation like:
```f(x) = data```
so to solve for x, we invert `f`:
```x = f_inverse(data)```
Of course, algorithmically inverting functions is Hard, so algex requires that we pass an inverse function explicitly. We do this using a Transform:  `f(x)` would be written like `Transform(S("x"), function=f, inverse=f_inverse)`, where `f` and `f_inverse` are user-defined functions.

As a simple example, here's how we parse an int from a string:
```python
from algex import Transform as T, S, solve
import math

data = {"some_number": "12"}
template = {"some_number": T(S("x"), function=str, inverse=int)}
```
The solution:
```python
>>> list(solve(template, data))
[{S("x"): 12}]
```
And a substitution:
```python
>>> output_template = T(S("x"), function=math.sqrt)
>>> list(substitute(output_template, solve(template, data)))
[3.4641016151377544]
```
Notice that we didn't pass an `inverse` to the `output_template`. In practice, we don't usually need to call both the function *and* its inverse - e.g. for the `output_template`, we only actually need to call the function. In this case, we can just leave out the direction we don't need. Similarly, for the `template` we only need the `inverse`, i.e.
```python
template = {"some_number": T(S("x"), inverse=int)}
```
works fine.

As a general rule: **if you're solving for a template, then Transforms in that template just need inverse functions; if you're substituting into a template, then Transforms in that template just need functions.** Omited functions/inverses are identity functions by default (i.e. they just return their input, so the transformation "does nothing").

We can also perform more complicated transformations, and mix them with other equation-solving operations. Here's an example where an annoying API passes us json nested as a string in another json structure:
```python
from algex import Transform as T, S, solve
import json

data = {"more_data": '{"name": "Alice"}'}
template = {"more_data": T({"name": S("name")}, inverse=json.loads)}
```
```python
>>> list(solve(template, data))
[{S('name'): 'Alice'}]
```

## Tips, Tricks and Gotchas
### Solve is Asymmetric
The `solve()` function solves for all variables on the left-hand side (first input), in terms of the data on the right-hand side (second input). Differences in how the two sides are treated:
- if there are any Symbols on the right, they will be treated as data
- "extra" data on the right is ignored, while "extra" data on the left is treated as a filter condition (see next section)
### Filtering
We can include constants on the left-hand side of the equation (i.e. in the template) in order to filter. For example, we can pick out names of people with red hats:
```python
>>> data = [{"name": "mario", "hat_color": "red"},
		{"name": "luigi", "hat_color": "green"},
		{"name": "santa", "hat_color": "red"}]
>>> template = [{"name": S("name"), "hat_color": "red"}]
>>> list(solve(template, data))
[{S('name'): 'mario'}, {S('name'): 'santa'}]
```
### Copy Transformations
Suppose we have a list of people:
```python
data = [{"name": "mario", "hat_color": "red"},
		{"name": "luigi", "hat_color": "green"},
		{"name": "santa", "hat_color": "red"}]
```
We want to extract all the names, but *also* count how many people are in the list, both while solving (i.e. not at substitution time). We could extract all the names with a template like `[{"name": S("name")}]`, or we could count the number of people in the list with `Transform(S("count"), inverse = lambda l: len(l))`, but how can we do them both at the same time? Doing either one "captures" that chunk of data; we need to somehow obtain two copies of the data so that we can use one sub-template for each.

This is the use-case for a copy Transformation:
```python
template = Transform({
	"copy1": [{"name": S("name")}],
	"copy2": Transform(S("count"), inverse = len)
}, inverse = lambda l: {"copy1": l, "copy2": l})
```
Let's walk through the equation-solving step-by-step:
 - Step 1: `Transform(..., inverse = lambda l: {"copy1": l, "copy2": l}) = data`, so we apply the inverse function on both sides. That inverse produces two copies of the data.
 - Step 2: `{"copy1": [{"name": S("name")}], "copy2": Transform(S("count"), inverse = len)} = {"copy1": data, "copy2": data}`
 - Step 3: `[{"name": S("name")}] = data` and `Transform(S("count"), inverse = lambda l: len(l))} = data`. We now solve for `S("name")` and `S("count")` in separate sub-problems, each with its own copy of the data.

Copy transformations are the main tool for a lot of the trickier problems which come up in using algex, so I recommend working through this example at a whiteboard or with pencil and paper if you plan to use the library extensively.

## Installation
Clone or download this repo, then run `python3 setup.py install`. Also take a look at test.py for several more examples, including some features not (yet) covered in this doc.

