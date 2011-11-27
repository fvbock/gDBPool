gDBPool
=======

gDBPool is a connection and interaction pooling library for/based on gevent.


Although gDBPool _should_ be able to work with all DB-API 2.0 compliant drivers
(I did not test this), the main db/driver it is written for is Postgres (9.x+ if
you want to use the asynchronous LISTEN/NOTIFY features in a meaningful way.
Previous versions supported LISTEN/NotifY but no customized payloads...) and
psycopg2.


gevent 0.13.6 is listed in `requirements.txt` but first tests with gevent 1.0a3
all worked fine.


gDBPool provides provides 2 main classes to work with in applications:


`DBConnectionPool` and `DBInteractionPool`.


`DBConnectionPool` is a connection pool with a `get()` and `put()` method to get
connections from the pool and puting them back.


Both functions take a timeout (get defaulting to no timeout, put defaulting to a
timeout of 1 second). Additionally the get function takes an argument
`auto_commit` to set the transaction isolation level of the connection to
`ISOLATION_LEVEL_AUTOCOMMIT`. putting the connection back will reset the level to
the default of `ISOLATION_LEVEL_READ_COMMITTED`. (the levels `read_uncommited`,
`read_repeatable`, and `serializable` will be added soon - see TODO)


`DBInteractionPool` manages one or more pools and provides a `run()` method to
run interactions (plain sql queries passed in or functions that take an
argument `conn`).

`DBInteractionPool` will run the interactions on either a pool that gets named
as an argument to the `run()` method or will use a default - depending on
whether the interactions is marked as a read_only interaction (no side-effects)
or not. As default an interaction with side-effects is assumed (in other words
a write query).

This is aimed at systems that have ie. a (single) master (write) and multiple
slaves to run read_only interactions on.

Besides the `run()` method `DBInteractionPool` provides a `listen_on()` method
to use the LISTEN/NOTIFY feature of Postgres. Most importantly this method takes
the name of the channel to listen on, a result_queue that the events are written
to (a `gevent.queue.Queue()`) and a cancel_event (a `gevent.event.Event()`) as
parameters. When the cancel_event is set the loop listening to events from the
db breaks and unregisters the result_queue.

Internally it uses a `PGChannelListener` singleton (per channel) to LISTEN and
just subscribes the result_queue to it if other queues are already listening
on that channel.



# Installation #

install the required packages:

    $ pip install -r requirements.txt

then install the package itself

    $ sudo python setup.py install


# Examples #

in the `tests` folder is a `test_schema.sql`. load that into a db called `gdbpool_test`
if you want to run these examples:

    $ psql -U postgres
    psql (9.0.5)
    Type "help" for help.

    postgres=# CREATE DATABASE gdbpool_test;
    CREATE DATABASE
    postgres=# \c gdbpool_test
    You are now connected to database "gdbpool_test".
    gdbpool_test=# \i /home/morpheus/data/dev/python/gevent/gDBPool/tests/test_schema.sql
    psql:/home/morpheus/data/dev/python/gevent/gDBPool/tests/test_schema.sql:7: NOTICE:  CREATE TABLE will create implicit sequence "test_values_id_seq" for serial column "test_values.id"
    psql:/home/morpheus/data/dev/python/gevent/gDBPool/tests/test_schema.sql:7: NOTICE:  CREATE TABLE / PRIMARY KEY will create implicit index "test_values_pkey" for table "test_values"
    CREATE TABLE
    INSERT 0 1000000
    CREATE RULE
    CREATE RULE
    gdbpool_test=#

create a `DBInteractionPool` with an internal derfault connection pool that has
16 connections. Logging is turned on.

    dsn = "host=127.0.0.1 port=5432 user=postgres dbname=gdbpool_test"
    ipool = DBInteractionPool( dsn, pool_size = 16, do_log = True )

and then run a query on it:

    sql = """
    SELECT val1, count(id) FROM test_values WHERE val2 = %s GROUP BY val1 order by val1;
    """
    async_res = ipool.run( sql )
    res = async_res.get()

or a function:

    def interaction( conn ):
        curs = conn.cursor()
        sql = """
        SELECT val1, val2, count(id) FROM test_values GROUP BY val1, val2 order by val1, val2;
        """
        curs.execute( sql )
        res = curs.fetchall()
        curs.close()
        return res

    async_res = self.ipool.run( interaction )
    res = async_res.get()

`run()` returns a `gevent.event.AsyncResult`.

to use `listen_on()`  you will need to run a loop that gets and handles the
data from the LISTEN stream. Have a look at the `tests/test_schema.sql` to see
how the RULES are set up to have Postgres send events. Check the function/test
`test_listen_on()` in `tests/tests.py` for a more complete example:

    rq = gevent.queue.Queue( maxsize = None )
    stop_event = gevent.event.Event()
    gevent.spawn( self.ipool.listen_on, result_queue = rq,
                  channel_name = 'notify_test_values',
                  cancel_event = stop_event )
    while 1:
        """ you will need something to break out of the loop and to set()
            the stop_event at the end."""
        if some_condition == True:
            break
        try:
            notify = rq.get_nowait()
            print notify
        except QueueEmptyException:
            gevent.sleep( 0.01 )

    stop_event.set()




# TODO #

* add all transaction isolation levels from postgres/psycopg to `DBConnectionPool.get`
and `DBConnectionPool.put`

* write more tests - esp. for multiple pools

* let `DBInteractionPool.run()` take a list of interactions and run then in parallel

* do more tests with gevent 1.0a

* add the DEC2FLOAT extension

* write more examples and add more info to this README...

