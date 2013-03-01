# -*- coding: utf-8 -*-

import sys

from django import VERSION
from django.db.models.sql.constants import SINGLE
from django.db.models.query_utils import QueryWrapper
from django.db.models.query import QuerySet
from django.db.models.sql.query import Query
from django.db.models.sql.where import EmptyShortCircuit, WhereNode
from django.db import models

from .query_utils import select_query, update_query

class HStoreWhereNode(WhereNode):
    def make_atom(self, child, qn, connection):
        lvalue, lookup_type, value_annot, param = child
        kwargs = VERSION[:2] >= (1, 3) and {'connection': connection} or {}
        if lvalue.field.db_type(**kwargs) == 'hstore':
            try:
                lvalue, params = lvalue.process(lookup_type, param, connection)
            except EmptyShortCircuit:
                raise EmptyResultSet
            field = self.sql_for_columns(lvalue, qn, connection)
            if lookup_type == 'exact':
                if isinstance(param, dict):
                    return ('%s = %%s' % field, [param])
                else:
                    raise ValueError('invalid value')
            elif lookup_type == 'contains':
                if isinstance(param, dict):
                    return ('%s @> %%s' % field, [param])
                elif isinstance(param, (list, tuple)):
                    if param:
                        return ('%s ?& %%s' % field, [param])
                    else:
                        raise ValueError('invalid value')
                elif isinstance(param, basestring):
                    return ('%s ? %%s' % field, [param])
                else:
                    raise ValueError('invalid value')
            else:
                raise TypeError('invalid lookup type')
        else:
            return super(HStoreWhereNode, self).make_atom(child, qn, connection)


class HStoreQuery(Query):
    def __init__(self, model):
        super(HStoreQuery, self).__init__(model, HStoreWhereNode)


class HStoreQuerysetMixin(object):
    def __init__(self, model=None, query=None, using=None):
        query = query or HStoreQuery(model)
        super(HStoreQuerysetMixin, self).__init__(model=model, query=query, using=using)
    
    @select_query
    def hkeys(self, query, attr):
        """
        Enumerates the keys in the specified hstore.
        """
        query.add_extra({'_': 'akeys("%s")' % attr}, None, None, None, None, None)
        result = query.get_compiler(self.db).execute_sql(SINGLE)
        return (result[0] if result else [])

    @select_query
    def hpeek(self, query, attr, key):
        """
        Peeks at a value of the specified key.
        """
        query.add_extra({'_': '%s -> %%s' % attr}, [key], None, None, None, None)
        result = query.get_compiler(self.db).execute_sql(SINGLE)
        if result and result[0]:
            field = self.model._meta.get_field_by_name(attr)[0]
            return field._value_to_python(result[0])

    @select_query
    def hslice(self, query, attr, keys):
        """
        Slices the specified key/value pairs.
        """
        query.add_extra({'_': 'slice("%s", %%s)' % attr}, [keys], None, None, None, None)
        result = query.get_compiler(self.db).execute_sql(SINGLE)
        if result and result[0]:
            field = self.model._meta.get_field_by_name(attr)[0]
            return dict((key, field._value_to_python(value)) for key, value in result[0].iteritems())
        return {}

    @update_query
    def hremove(self, query, attr, keys):
        """
        Removes the specified keys in the specified hstore.
        """
        value = QueryWrapper('delete("%s", %%s)' % attr, [keys])
        field, model, direct, m2m = self.model._meta.get_field_by_name(attr)
        query.add_update_fields([(field, None, value)])
        return query

    @update_query
    def hupdate(self, query, attr, updates):
        """
        Updates the specified hstore.
        """
        value = QueryWrapper('"%s" || %%s' % attr, [updates])
        field, model, direct, m2m = self.model._meta.get_field_by_name(attr)
        query.add_update_fields([(field, None, value)])
        return query


class HStoreQueryset(HStoreQuerysetMixin, QuerySet):
    pass


class HStoreManagerMixin(object):
    """
    Object manager which enables hstore features.
    """
    use_for_related_fields = True

    def hkeys(self, attr):
        return self.get_query_set().hkeys(attr)

    def hpeek(self, attr, key):
        return self.get_query_set().hpeek(attr, key)

    def hslice(self, attr, keys, **params):
        return self.get_query_set().hslice(attr, keys)


class HStoreManager(HStoreManagerMixin, models.Manager):
    def get_query_set(self):
        return HStoreQueryset(self.model, using=self._db)

# Signal attaching
from psycopg2.extras import register_hstore

def register_hstore_handler(connection, **kwargs):
    if sys.version_info.major < 3:
        register_hstore(connection.cursor(), globally=True, unicode=True)
    else:
        register_hstore(connection.cursor(), globally=True)
