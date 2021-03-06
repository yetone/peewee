import threading
import unittest

from peewee import *
from playhouse.sqlite_kv import KeyStore


class KeyStoreTestCase(unittest.TestCase):
    def setUp(self):
        self.kv = KeyStore()
        self.ordered_kv = KeyStore(ordered=True)
        self.kv.clear()

    def test_storage(self):
        self.kv['a'] = 'A'
        self.kv['b'] = 1
        self.assertEqual(self.kv['a'], 'A')
        self.assertEqual(self.kv['b'], 1)
        self.assertRaises(KeyError, self.kv.__getitem__, 'c')

        del(self.kv['a'])
        self.assertRaises(KeyError, self.kv.__getitem__, 'a')

        self.kv['a'] = 'A'
        self.kv['c'] = 'C'
        self.assertEqual(self.kv[self.kv.key << ('a', 'c')], ['A', 'C'])

        self.kv[self.kv.key << ('a', 'c')] = 'X'
        self.assertEqual(self.kv['a'], 'X')
        self.assertEqual(self.kv['b'], 1)
        self.assertEqual(self.kv['c'], 'X')

        del(self.kv[self.kv.key << ('a', 'c')])
        self.assertRaises(KeyError, self.kv.__getitem__, 'a')
        self.assertRaises(KeyError, self.kv.__getitem__, 'c')
        self.assertEqual(self.kv['b'], 1)

    def test_container_properties(self):
        self.kv['x'] = 'X'
        self.kv['y'] = 'Y'
        self.assertEqual(len(self.kv), 2)
        self.assertTrue('x' in self.kv)
        self.assertFalse('a' in self.kv)

    def test_dict_methods(self):
        self.ordered_kv['a'] = 'A'
        self.ordered_kv['c'] = 'C'
        self.ordered_kv['b'] = 'B'
        self.assertEqual(list(self.ordered_kv.keys()), ['a', 'b', 'c'])
        self.assertEqual(list(self.ordered_kv.values()), ['A', 'B', 'C'])
        self.assertEqual(list(self.ordered_kv.items()), [
            ('a', 'A'),
            ('b', 'B'),
            ('c', 'C'),
        ])

    def test_iteration(self):
        self.ordered_kv['a'] = 'A'
        self.ordered_kv['c'] = 'C'
        self.ordered_kv['b'] = 'B'

        items = list(self.ordered_kv)
        self.assertEqual(items, [
            ('a', 'A'),
            ('b', 'B'),
            ('c', 'C'),
        ])

    def test_shared_mem(self):
        self.kv['a'] = 'xxx'
        self.assertEqual(self.ordered_kv['a'], 'xxx')

        def set_k():
            kv_t = KeyStore()
            kv_t['b'] = 'yyy'
        t = threading.Thread(target=set_k)
        t.start()
        t.join()

        self.assertEqual(self.kv['b'], 'yyy')

    def test_get(self):
        self.kv['a'] = 'A'
        self.kv['b'] = 'B'
        self.assertEqual(self.kv.get('a'), 'A')
        self.assertEqual(self.kv.get('x'), None)
        self.assertEqual(self.kv.get('x', 'y'), 'y')

        self.assertEqual(
            list(self.kv.get(self.kv.key << ('a', 'b'))),
            ['A', 'B'])
        self.assertEqual(
            list(self.kv.get(self.kv.key << ('x', 'y'))),
            [])

    def test_pop(self):
        self.ordered_kv['a'] = 'A'
        self.ordered_kv['b'] = 'B'
        self.ordered_kv['c'] = 'C'

        self.assertEqual(self.ordered_kv.pop('a'), 'A')
        self.assertEqual(list(self.ordered_kv.keys()), ['b', 'c'])

        self.assertRaises(KeyError, self.ordered_kv.pop, 'x')
        self.assertEqual(self.ordered_kv.pop('x', 'y'), 'y')

        self.assertEqual(
            list(self.ordered_kv.pop(self.ordered_kv.key << ['b', 'c'])),
            ['B', 'C'])

        self.assertEqual(list(self.ordered_kv.keys()), [])
