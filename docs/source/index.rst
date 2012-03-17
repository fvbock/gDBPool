.. gDBPool documentation master file, created by
   sphinx-quickstart on Sun Feb  5 16:53:36 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. highlight:: python
.. currentmodule:: gDBPool

===========================================================================
gDBPool - asynchronous database interaction pooling for gevent and Postgres
===========================================================================

gDBPool is a gevent and postgres based library providing interaction and connection pooling.
The original motivation to build gDBPool was to implement a connection pool for gevent. With gevent being an asynchronous networking library, and having `Postgres asynchronous event capabilities <http://initd.org/psycopg/docs/advanced.html#asynchronous-notifications>`_ with `LISTEN <http://www.postgresql.org/docs/9.1/static/sql-listen.html>`_ and `NOTIFY <http://www.postgresql.org/docs/9.1/static/sql-notify.html>`_ building support for it was pretty much natural. Of course this makes the library bound to Postgres and psycopg2, but for now that is fine.
The initial version had support for the use of different DB-API libraries for the non async features but support has been dropped for now.

gDBPool features
----------------

* multiple connection pool support (including read-only/write pool distinction)
* running plain SQL queries as well as more complex transactions that are encapsulated in a function or method
* partial transaction execution (ie. to run an interaction that obtains a row level lock, and then - maybe after some other operations - run a second interaction that uses that lock and in the end commits the transaction).
* ayncronous notification/event support (postgres LISTEN/NOTIFY)


.. toctree::
   :maxdepth: 5

.. include:: ../../README.rst
    :start-after: end-summary


Quick tests/examples
--------------------

if you want to run the following basic tests you will need to create a test database first. Log into Postgres and then run the following

.. code-block:: psql

    postgres=# CREATE DATABASE gdbpool_test;
    CREATE DATABASE
    postgres=# \c gdbpool_test
    You are now connected to database "gdbpool_test".
    gdbpool_test=# \i <PATH_TO_GDBPOOL_REPO>/gDBPool/tests/test_schema.sql
    psql:<PATH_TO_GDBPOOL_REPO>/gDBPool/tests/test_schema.sql:7: NOTICE:  CREATE TABLE will create implicit sequence "test_values_id_seq" for serial column "test_values.id"
    psql:<PATH_TO_GDBPOOL_REPO>/gDBPool/tests/test_schema.sql:7: NOTICE:  CREATE TABLE / PRIMARY KEY will create implicit index "test_values_pkey" for table "test_values"
    CREATE TABLE
    INSERT 0 1000000
    CREATE RULE
    CREATE RULE
    gdbpool_test=#

Now you can create a :class:`interaction_pool.DBInteractionPool` instance. All the following examples assume this has been run.

.. code-block:: python

    from gdbpool.interaction_pool import DBInteractionPool
    dsn = "host=127.0.0.1 port=5432 user=postgres dbname=gdbpool_test"
    ipool = DBInteractionPool( dsn, pool_size = 16, do_log = True )


Run a plain SQL query
^^^^^^^^^^^^^^^^^^^^^^

We have an interaction_pool instance and can start running queries intaractions on it:

.. sourcecode:: ipython

    In [6]: ipool.run( "SELECT * FROM test_values WHERE id = %s;", [ 123 ] ).get()
    Out[6]: [{'id': 123, 'val1': 7, 'val2': 9}]

    In [7]: async_result = ipool.run( "SELECT * FROM test_values WHERE id = %s;", [ 123 ] )

    In [8]: async_result
    Out[8]: <gevent.event.AsyncResult at 0x26e8e90>

    In [9]: async_result.get()
    Out[9]: [{'id': 123, 'val1': 7, 'val2': 9}]

    In [10]: ipool.run( "SELECT * FROM test_values WHERE id = %s;", [ 123 ] ).get()
    Out[10]: [{'id': 123, 'val1': 7, 'val2': 9}]

run() (instantly) returns a :class:`gevent.AsyncResult` on which the blocking call get() can be made.


Run an a function on the pool
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Instead of running queries interactions can also defined as functions (or methods) that take an argument `conn` and optionally an argument `cursor`. This can be useful to have more granular/direct control on transactional behaviour.

.. sourcecode:: ipython

    In [37]: def interaction( conn ):
       ....:         curs = conn.cursor()
       ....:         sql = """
       ....:         SELECT val1, count(id) FROM test_values GROUP BY val1 order by val1;
       ....:         """
       ....:         curs.execute( sql )
       ....:         res = curs.fetchall()
       ....:         curs.close()
       ....:         return res
       ....:

    In [38]:

    In [38]: ipool.run( interaction ).get()
    Out[38]:
    [{'count': 55673L, 'val1': 1},
     {'count': 110882L, 'val1': 2},
     {'count': 111491L, 'val1': 3},
     {'count': 111101L, 'val1': 4},
     {'count': 111075L, 'val1': 5},
     {'count': 111154L, 'val1': 6},
     {'count': 111071L, 'val1': 7},
     {'count': 110875L, 'val1': 8},
     {'count': 110905L, 'val1': 9},
     {'count': 55773L, 'val1': 10},
     {'count': 125L, 'val1': 11}]


Debugging a query
^^^^^^^^^^^^^^^^^^^

For debugging purposes the interaction pool can just print the SQL that *would* be run:

.. sourcecode:: ipython

    In [33]: ipool.run( "SELECT * FROM test_values WHERE id = %s;", [ 123 ], dry_run = True ).get()
    Out[33]: 'SELECT * FROM test_values WHERE id = 123;'


Listen for asyncronous NOTIFY events
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To listen on a postgres channel for events

.. sourcecode:: ipython

    In [1]: import gevent

    In [2]: from gevent import monkey; monkey.patch_all()

    In [3]: from gevent.queue import Queue
    The history saving thread hit an unexpected error (NotImplementedError('gevent is only usable from a single thread',)).History will not be written to the database.

    In [4]: from gevent.queue import Empty as QueueEmptyException

    In [5]:

    In [5]: from gdbpool.interaction_pool import DBInteractionPool

    In [6]: dsn = "host=127.0.0.1 port=5432 user=postgres dbname=gdbpool_test"

    In [7]: ipool = DBInteractionPool( dsn, pool_size = 16, do_log = True )
    2012-03-18 02:10:40,944 $ poolsize: 16

    In [8]:

    In [8]: rq = Queue( maxsize = None )

    In [9]: stop_event = gevent.event.Event()

    In [10]: gevent.spawn( ipool.listen_on, result_queue = rq, channel_name = 'notify_test_values', cancel_event = stop_event )
    Out[10]: <Greenlet at 0x176d160: <bound method DBInteractionPool.listen_on of <gdbpool.interaction_pool.DBInteractionPool object at 0x175ce10>>(channel_name='notify_test_values', result_queue=<Queue at 0x175cd50 maxsize=None>, cancel_event=<gevent.event.Event object at 0x175cdd0>)>

    In [11]: while 1:
            try:
                notify = rq.get_nowait()
                print "NOTIFY:", notify
                break
            except QueueEmptyException:
                gevent.sleep( 0.1 )
       ....:

The loop will now wait for a NOTIFY to be fired from the db:

.. code-block:: psql

    gdbpool_test=# UPDATE test_values SET val1 = 123 WHERE id = 459;
     pg_notify
    -----------

    (1 row)

    UPDATE 1
    gdbpool_test=#

which will result in the loop breaking and the following output. we set the `stop_event` so that the PGChannelListener will stop listening for more events.

.. sourcecode:: ipython

    NOTIFY: {'val1': '123', 'id': '459'}

    In [12]:

    In [12]: stop_event.set()


.. include:: classes/index.rst



Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


