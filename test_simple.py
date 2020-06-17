from algex import S, solve, substitute

import unittest


class TestSimple(unittest.TestCase):
    # Test one: single match
    def test_single_match(self):
        data = {'name': 'john'}
        template = {'name': S('name')}

        m = solve(template, data)
        self.assertEqual(list(m), [{S('name'): 'john'}])
        result = list(substitute(template, m))
        self.assertEqual(result, [data])  # Note the asymmetry: format_simple returns a list

    # Test 2: Two matches
    def test_two_matches(self):
        data = [{'name': 'john'}, {'name': 'abe'}]
        match_template = [{'name': S('name')}]
        format_template = {'name': S('name')}  # Again, asymmetry.

        m = solve(match_template, data)
        self.assertEqual(list(m), [{S('name'): 'john'}, {S('name'): 'abe'}])
        result = list(substitute(format_template, m))
        self.assertEqual(result, data)

    # Test 3: Cartesian product
    def test_cartesian_product(self):
        data = [{'name': 'john', 'addresses': [{'state': 'CA'}, {'state': 'CT'}]},
                {'name': 'allan', 'addresses': [{'state': 'CA'}, {'state': 'WA'}]}]
        match_template = [{'name': S('name'), 'addresses': [{'state': S('state')}]}]

        m = list(solve(match_template, data))
        self.assertEqual(m, [{S('name'): 'john', S('state'): 'CA'},
                             {S('name'): 'john', S('state'): 'CT'},
                             {S('name'): 'allan', S('state'): 'CA'},
                             {S('name'): 'allan', S('state'): 'WA'}])

    # Test 4: Symbol list
    def test_symbol_list(self):
        data = [{'name': 'john', 'addresses': [{'state': 'CA'}, {'state': 'CT'}]},
                {'name': 'allan', 'addresses': [{'state': 'CA'}, {'state': 'WA'}]}]
        match_template = [{'name': S('name'), 'addresses': [{'state': S('state')}]}]
        format_template = {S('name'): S('name')}

        m = solve(match_template, data)
        result = list(substitute(format_template, m))
        self.assertEqual(result, [{S('name'): 'john'}, {S('name'): 'allan'}])

    # Test 5: Search
    def test_search(self):
        data = [{'name': 'john', 'state': 'CT'}, {'name': 'allan', 'state': 'WA'}]
        template = [{'name': S('name'), 'state': 'WA'}]

        m = list(solve(template, data))
        self.assertEqual(m, [{S('name'): 'allan'}])

    # Test 6: Uniqueing
    def test_unique(self):
        data = [{'name': 'john', 'addresses': [{'state': 'CA'}, {'state': 'CT'}]},
                {'name': 'allan', 'addresses': [{'state': 'CA'}, {'state': 'WA'}]}]
        template = [{'name': S('name'), 'addresses': [{'state': S('state')}]}]
        format_template = {S('state'): S('state')}

        m = solve(template, data)
        result = list(substitute(format_template, m))
        self.assertEqual(result, [{S('state'): 'CA'}, {S('state'): 'CT'}, {S('state'): 'WA'}])

    # Test 7: Search on index w/in list
    def test_index_nested_in_list(self):
        data = [{'name': 'john', 'addresses': [{'state': 'CA'}, {'state': 'CT'}]},
                {'name': 'allan', 'addresses': [{'state': 'CA'}, {'state': 'WA'}]}]
        template = [{'addresses': [{'state': 'CT'}], 'name': S('name')}]

        m = list(solve(template, data))
        self.assertEqual(m, [{S('name'): 'john'}])

    # Test 8: Irrelevant info on one branch
    def test_irrelevant_side_info(self):
        data = {'u': [1, 2], 'v': [3, 4]}
        template = {'u': [S('u')], 'v': [S('v')]}
        format_template = {S('u'):S('u')}

        m = solve(template, data)
        result = list(substitute(format_template, m))
        self.assertEqual(result, [{S('u'): 1}, {S('u'): 2}])

if __name__ == '__main__':
    unittest.main()
