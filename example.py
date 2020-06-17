from __init__ import S, solve, substitute

template = {
    "person": {
	    "first_name": S("x"),
	    "last_name": S("y")
	}
}

data = {
	"person": {
		"first_name": "Alice",
		"last_name": "Liddell"
	}
}

solutions = solve(template, data)
