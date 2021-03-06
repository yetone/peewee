"""
Provides a simple, in-memory key/value store using Sqlite.
"""

import itertools
import pickle
from peewee import *
from peewee import Leaf

try:
    from playhouse.apsw_ext import APSWDatabase
    def KeyValueDatabase(db_name):
        return APSWDatabase(db_name)
except ImportError:
    def KeyValueDatabase(db_name):
        return SqliteDatabase(db_name, check_same_thread=False)

Sentinel = type('Sentinel', (object,), {})

key_value_db = KeyValueDatabase(':memory:')


class KV(Model):
    key = CharField(index=True, primary_key=True)
    value = BlobField()

    class Meta:
        database = key_value_db


class KeyStore(object):
    def __init__(self, ordered=False, model=None):
        self.model = model or KV
        self.key = self.model.key
        self.value = self.model.value

        self._db = self.model._meta.database
        self._compiler = self._db.compiler()
        self._ordered = ordered

        self._db.create_table(self.model, True)

    def __contains__(self, key):
        return self.model.select().where(self.key == key).exists()

    def __len__(self):
        return self.model.select().count()

    def convert_expr(self, expr):
        if not isinstance(expr, Leaf):
            return (self.key == expr), True
        return expr, False

    def __getitem__(self, expr):
        converted, is_single = self.convert_expr(expr)
        query = self.query(self.value).where(converted)
        result = [pickle.loads(item[0]) for item in query]
        if len(result) == 0 and is_single:
            raise KeyError(expr)
        elif is_single:
            return result[0]
        return result

    def _upsert(self, key, value):
        sets, params = self._compiler.parse_field_dict({
            self.key: key,
            self.value: value})
        fields, interp = zip(*sets)
        sql = 'INSERT OR REPLACE INTO %s (%s) VALUES (%s)' % (
            self._compiler.quote(self.model._meta.db_table),
            ', '.join(fields),
            ', '.join(interp))
        self._db.execute_sql(sql, params, True)

    def __setitem__(self, expr, value):
        pickled_value = pickle.dumps(value)
        if isinstance(expr, Leaf):
            update = {self.value.name: pickled_value}
            self.model.update(**update).where(expr).execute()
        else:
            self._upsert(expr, pickled_value)

    def __delitem__(self, expr):
        converted, _ = self.convert_expr(expr)
        self.model.delete().where(converted).execute()

    def query(self, *select):
        query = self.model.select(*select).tuples()
        if self._ordered:
            query = query.order_by(self.key)
        return query

    def __iter__(self):
        for k, v in self.query().execute():
            yield k, pickle.loads(v)

    def keys(self):
        for row in self.query(self.key):
            yield row[0]

    def values(self):
        for row in self.query(self.value):
            yield pickle.loads(row[0])

    def items(self):
        return iter(self)

    def get(self, k, default=None):
        try:
            return self[k]
        except KeyError:
            return default

    def pop(self, k, default=Sentinel):
        with self._db.transaction():
            expr, is_single = self.convert_expr(k)
            try:
                res = self[k]
            except KeyError:
                if default is Sentinel:
                    raise
                return default
            del(self[expr])
        return res

    def clear(self):
        self.model.delete().execute()
