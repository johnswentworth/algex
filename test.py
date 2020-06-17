#from .match import match
#from .format import format
#from .symbol import S, Nullable, TransSymbol as Trans
from __init__ import S, Transform as Trans, Nullable, solve, substitute

import random, unittest


class TestFull(unittest.TestCase):
    # Test 1: Single match, no lists
    def test_single_match(self):
        data = {'name': 'john'}
        template = {'name': S('name')}

        m = solve(template, data)
        result = substitute(template, m)
        self.assertEqual(list(result), [data])

    # Test 2: Two matches
    def test_two_matches(self):
        data = [{'name':'john'}, {'name':'abe'}]
        template = [{'name': S('name')}]

        m = solve(template, data)
        result = substitute(template[0], m)
        self.assertEqual(list(result), data)

    # Test 3: Transposition
    def test_transposition(self):
        data = [{'name':'john', 'addresses':[{'state':'CA'}, {'state':'CT'}]},
                {'name': 'allan', 'addresses':[{'state':'CA'}, {'state':'WA'}]}]
        match_template = [{'name':S('name'), 'addresses':[{'state':S('state')}]}]
        format_template = {'address':{'state':S('state')}, 'names':[S('name')]}
        expected = [{'address':{'state':'CA'}, 'names':['john', 'allan']},
                    {'address':{'state':'CT'}, 'names':['john']},
                    {'address':{'state':'WA'}, 'names':['allan']}]

        m = solve(match_template, data)
        result = substitute(format_template, m)
        self.assertEqual(list(result), expected)
    
    # Test 4: Cartesian product stress test
    def test_cartesian_product(self):
        data = {'u':[random.random() for i in range(1000)],
                'v':[random.random() for i in range(1000)],
                'w':[random.random() for i in range(1000)],
                'x':[random.random() for i in range(1000)],
                'y':[random.random() for i in range(1000)],
                'z':[random.random() for i in range(1000)]}
        template = {'u':[S('u')], 'v':[S('v')], 'w':[S('w')], 'x':[S('x')], 'y':[S('y')], 'z':[S('z')]}

        m = solve(template, data) # Should take several decades if cartesian products are handled naively
        result = substitute(template, m)
        self.assertEqual(list(result), [data])
    
    # Test 5: Nullable
    def test_nullable(self):
        data = {}
        template = {'person': Nullable([{'name':S('name')}])}

        m = solve(template, data).get_single()  # Should not raise an exception

    # Test 6: Transformation closed-loop test
    def test_transformation(self):
        data = {'state':'California'}
        template = {'state': Trans(S('state'), function={'CA': 'California'}, inverse={'California': 'CA'})}

        m = solve(template, data)
        self.assertEqual(m.get_single()[S('state')], 'CA')

        result = substitute(template, m)
        self.assertEqual(list(result), [data])

    # Test 7: Transformation closed-loop test with function transformation
    def test_transformation_2(self):
        data = {'yrs': 12.5}
        parse_template = {'yrs': S('yrs')}
        format_template = {'residency': Trans(S('yrs'), int)}

        m = solve(parse_template, data)
        result = substitute(format_template, m)
        self.assertEqual(list(result), [{'residency': 12}])

    # Test 8: Join on a repeated symbol
    def test_join(self):
        data = {'names': [{'ssn': 123456789, 'name': 'mario'}, {'ssn': 987654321, 'name': 'luigi'}],
                'hats': [{'ssn': 123456789, 'hat_color': 'red'}, {'ssn': 987654321, 'hat_color': 'green'}]}
        match_template = {'names': [{'ssn': S('ssn'), 'name':S('name')}],
                          'hats': [{'ssn': S('ssn'), 'hat_color': S('color')}]}
        format_template = {'name': S('name'), 'ssn': S('ssn'), 'color': S('color')}
        # NOTE: one major drawback of the current code is that format() must USE a symbol in order to join on it.
        # E.g., this example would do a full cartesian product rather than a join if S('ssn') were omitted from format_template.
        expected = [{'name': 'mario', 'ssn': 123456789, 'color': 'red'},
                    {'name': 'luigi', 'ssn': 987654321, 'color': 'green'}]

        m = solve(match_template, data)
        result = substitute(format_template, m)
        self.assertEqual(list(result), expected)

    # Tests 9 & 10: More general Transformation usage
    def test_multi_transformation_forward(self):
        data = [{'name': 'john', 'addresses': [{'state': 'CA'}, {'state': 'CT'}]},
                {'name': 'allan', 'addresses': [{'state': 'CA'}, {'state': 'WA'}]}]
        match_template = [{'name': S('name'), 'addresses': [{'state': S('state')}]}]
        starts_j = lambda name: name[0] == 'j'
        format_template = {'address': {'state': S('state')}, 'names': Trans([S('name')], lambda names: list(filter(starts_j, names)))}
        expected = [{'address': {'state': 'CA'}, 'names': ['john']},
                    {'address': {'state': 'CT'}, 'names': ['john']},
                    {'address': {'state': 'WA'}, 'names': []}]

        m = solve(match_template, data)
        result = substitute(format_template, m)
        self.assertEqual(list(result), expected)

    def test_multi_transformation_reverse(self):
        data = {'names': [{'ssn': 'red', 'name': 'mario'}, {'ssn': 'green', 'name': 'luigi'}],
                'hats': [{'ssn': 123456789, 'hat_color': 'red'}, {'ssn': 987654321, 'hat_color': 'green'}]}
        switcheroo = lambda hat_entry: {'ssn': hat_entry['hat_color'], 'hat_color': hat_entry['ssn']}
        match_template = {'names': [{'ssn': S('ssn'), 'name':S('name')}],
                          'hats': [Trans({'ssn': S('ssn'), 'hat_color': S('color')}, inverse=switcheroo)]}
        format_template = {'name': S('name'), 'ssn': S('ssn'), 'color': S('color')}
        expected = [{'name': 'mario', 'ssn': 'red', 'color': 123456789},
                    {'name': 'luigi', 'ssn': 'green', 'color': 987654321}]

        m = solve(match_template, data)
        result = substitute(format_template, m)
        self.assertEqual(list(result), expected)

    # TransSymbol invertibility: things were failing if forward(reverse(x)) != x. Fixed now.
    def test_trans_list_bug(self):
        match_template = {
            "create_date": Trans(S('created_at'), inverse=lambda x: x + '!'),
            "actions": [{
                "date": S('velocify_action_date'),
            }]
        }

        template = {
            "created": S('created_at'),
            "velocify": {
                "actions": [{
                    "date": S('velocify_action_date'),
                }]
            }
        }

        data = {'create_date': '2017-12-12 07:39:06', 'actions': [{'date': '2017-12-11 11:40:56'}, {'date': '2017-12-18 11:49:56'}]}
        expected = {'created': '2017-12-12 07:39:06!', 'velocify': {'actions': [{'date': '2017-12-11 11:40:56'}, {'date': '2017-12-18 11:49:56'}]}}

        m = solve(match_template, data)
        result = substitute(template, m)
        self.assertEqual(list(result), [expected])

    # Test 12: Make sure TransSymbol doesn't swallow errors
    def test_trans_error(self):
        data = {'yrs': 'foo'}
        parse_template = {'yrs': S('yrs')}
        format_template = {'residency': Trans(S('yrs'), int)}

        m = solve(parse_template, data)
        err = None
        try:
            result = list(substitute(format_template, m))
        except ValueError as e:
            err = e
        self.assertIsNotNone(err)

if __name__ == '__main__':
    unittest.main(module='test')
