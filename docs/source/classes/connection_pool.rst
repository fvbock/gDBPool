=================
DBConnectionPool
=================

Manages connections, recycles them if requested to and monitors the connection state.


Class Documenation
-------------------

.. autoclass:: gdbpool.connection_pool.DBConnectionPool
   :members:
   :inherited-members:
   :private-members:
   :show-inheritance:


Transaction Isolation Level constants
--------------------------------------

When getting a connection from the pool one can set the transaction isolation level for that connection (the default being the same as postres: ISOLATION_LEVEL_READ_COMMITTED). These are the levelse that can be requested. (See also: `13.2. Transaction Isolation <http://www.postgresql.org/docs/9.1/static/transaction-iso.html>`_ and `Isolation level constants <http://initd.org/psycopg/docs/extensions.html#isolation-level-constants>`_)

The isolation level is being reset when the connection is put back onto the pool.

The constants can be imported from psycopg:

.. code-block:: python

    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT, \
        ISOLATION_LEVEL_READ_UNCOMMITTED, \
        ISOLATION_LEVEL_READ_COMMITTED, \
        ISOLATION_LEVEL_REPEATABLE_READ, \
        ISOLATION_LEVEL_SERIALIZABLE


.. data:: ISOLATION_LEVEL_AUTOCOMMIT

.. data:: ISOLATION_LEVEL_READ_UNCOMMITTED

.. data:: ISOLATION_LEVEL_READ_COMMITTED

.. data:: ISOLATION_LEVEL_REPEATABLE_READ

.. data:: ISOLATION_LEVEL_SERIALIZABLE
