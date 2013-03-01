postgresql
==========

Django PostgreSQL hstore and intarray extensions support

Usage
=====

The library provides three principal classes:

``postgresql.fields.DictionaryField``
    An ORM field which stores a mapping of string key/value pairs in an hstore column.
``postgresql.fields.ReferencesField``
    An ORM field which builds on DictionaryField to store a mapping of string keys to django object references, much like ForeignKey.
``postgresql.models.Manager``
    An ORM manager which provides much of the query functionality of the library.

Model definition is straightforward::

    from django.db import models

    import postgresql

    class Something(models.Model):
        name = models.CharField(max_length=32)
        data = postgresql.fields.DictionaryField(db_index=True)
        objects = postgresql.manager.Manager()

        def __unicode__(self):
            return self.name

You then treat the ``data`` field as simply a dictionary of string pairs::

    instance = Something.objects.create(name='something', data={'a': '1', 'b': '2'})
    assert instance.data['a'] == '1'

    empty = Something.objects.create(name='empty')
    assert empty.data == {}

    empty.data['a'] = '1'
    empty.save()
    assert Something.objects.get(name='something').data['a'] == '1'

You can issue indexed queries against hstore fields::

    # equivalence
    Something.objects.filter(data={'a': '1', 'b': '2'})

    # subset by key/value mapping
    Something.objects.filter(data__contains={'a': '1'})

    # subset by list of keys
    Something.objects.filter(data__contains=['a', 'b'])

    # subset by single key
    Something.objects.filter(data__contains='a')

You can also take advantage of some db-side functionality by using the manager::

    # identify the keys present in an hstore field
    >>> Something.objects.hkeys(id=instance.id, attr='data')
    ['a', 'b']

    # peek at a a named value within an hstore field
    # do the same, after filter
    >>> Something.objects.filter(id=instance.id).hpeek(attr='data', key='a')
    '1'

    # remove a key/value pair from an hstore field
    >>> Something.objects.filter(name='something').hremove('data', 'b')

The hstore methods on manager pass all keyword arguments aside from ``attr`` and ``key``
to ``.filter()``.

.. _hstore: http://www.postgresql.org/docs/9.0/interactive/hstore.html

