# -*- coding: utf-8 -*-

# Copyright 2011-2012 Florian von Bock (f at vonbock dot info)
#
# gDBPool - db connection pooling for gevent

__author__ = "Florian von Bock"
__email__ = "f at vonbock dot info"
__version__ = "0.1.3"


import gevent
from gevent import monkey; monkey.patch_all()
from psyco_ge import make_psycopg_green; make_psycopg_green()
import sys
assert 'gdbpool.psyco_ge' in sys.modules.keys()

import psycopg2
import traceback

from gevent.queue import Queue, Empty as QueueEmptyException
from gevent.event import AsyncResult
from types import FunctionType, MethodType, StringType
from psycopg2 import DatabaseError
psycopg2.extensions.register_type( psycopg2.extensions.UNICODE )
psycopg2.extensions.register_type( psycopg2.extensions.UNICODEARRAY )
from inspect import getargspec

from connection_pool import DBConnectionPool
from channel_listener import PGChannelListener
from gdbpool_error import DBInteractionException, DBPoolConnectionException, PoolConnectionException, StreamEndException


class DBInteractionPool( object ):
    """
    The DBInteractionPool manages `DBConnectionPool` instances and can run
    queries or functions (ie. several queries wrapped in a function) on one of
    these pools.
    """

    def __new__( cls, dsn, *args, **kwargs ):
        if not hasattr( cls, '_instance' ):
            cls._instance = object.__new__( cls )
        return cls._instance

    def __init__( self, dsn, pool_size = 10, pool_name = 'default',
                  do_log = False ):
        """
        :param string dsn: DSN for the default `class:DBConnectionPool`
        :param int pool_size: Poolsize of the first/default `class:DBConnectionPool`
        :param string pool_name: Keyname for the first/default `class:DBConnectionPool`
        :param bool do_log: Log to the console or not
        """

        if do_log == True:
            import logging
            logging.basicConfig( level = logging.INFO, format = "%(asctime)s %(message)s" )
            self.logger = logging.getLogger()
        self.do_log = do_log
        self.request_queue = Queue( maxsize = None )
        self.db_module = 'psycopg2'
        self.conn_pools = {}
        self.default_write_pool = None
        self.default_read_pool = None
        self.default_pool = None
        self.active_listeners = {}
        self.add_pool( dsn = dsn, pool_name = 'default', pool_size = pool_size,
                       default_write_pool = True, default_read_pool = True,
                       db_module = self.db_module )

    def __del__( self ):
        if self.do_log:
            self.logger.info( "__del__ DBInteractionPool" )
        for p in self.conn_pools:
            self.conn_pools[ p ].__del__()

    def __call__( self, *args, **kwargs ):
        """ syntactic sugar for `:ref:DBInteractionPool.run` """
        return self.run( *args, **kwargs  )

    def add_pool( self, dsn = None, pool_name = None, pool_size = 10,
                  default_write_pool = False, default_read_pool = False,
                  default_pool = False, db_module = 'psycopg2' ):
        """
        Add a named `:class:DBConnectionPool`

        :param string dsn: dsn
        :param string pool_name: a name for the pool to identify it inside the DBInteractionPool
        :param int pool_size: Number of connections the pool should have.
        :param bool default_write_pool: Should the added pool used as the default pool for write operations?
        :param bool default_read_pool: Should the added pool used as the default pool for read operations?
        :param bool default_pool: Should the added pool used as the default pool? (*must* be a write pool)
        :param string db_module: name of the DB-API module to use

        .. note::
            db_module right now ONLY supports psycopg2 and the option most likely will be removed in the future
        """

        if not self.conn_pools.has_key( pool_name ):
            self.conn_pools[ pool_name ] = DBConnectionPool( dsn, db_module = self.db_module,
                                                             pool_size = pool_size, do_log = self.do_log )
            if default_write_pool:
                self.default_write_pool = pool_name
                if self.default_pool or self.default_pool is None:
                    self.default_pool = pool_name
            if default_read_pool:
                self.default_read_pool = pool_name
        else:
            raise DBInteractionException( "Already have a pool with the name: %s. ConnectionPool not added!" % ( pool_name, ) )

    @property
    def pool( self ):
        return self.conn_pools[ self.default_pool ]

    def run( self, interaction = None, interaction_args = None,
             get_result = True, is_write = True, pool = None, conn = None,
             cursor = None, partial_txn = False, dry_run = False, *args,
             **kwargs ):
        """
        Run an interaction on one of the managed `:class:DBConnectionPool` pools.

        :param function|method interaction: The interaction to run. Either a SQL string or a function that takes at least a parameter `conn`.
        :param string interaction_args: None,
        :param bool get_result: call and return cursor.fetchall() when True - otherwise just return True as result if no exception was raised.
        :param bool is_write: If the interaction has no side-effects set to `False`. Without naming a pool the default_read pool would be used.
        :param string pool: Keyname of the pool to get the a connection from
        :param connection conn: Pass in a `Connection` instead of getting one from the pool. (ie. for locks in transactions that span several interactions. Use `partial_txn = True` to retrieve the Connection and then pass it into the next interaction run.)
        :param cursor cursor: Pass in a `Cursor` instead of getting one from the `Connection` (ie. for locks in transactions that span several interactions.  Use `partial_txn = True` to retrieve the Cursor and then pass it into the next interaction run.)
        :param bool partial_txn: Return connection and cursor after executing the interaction (ie. for locks in transactions that span several interactions)
        :param bool dry_run: Run the query with `mogrify` instead of `execute` and output the query that would have run. (Only applies to query interactions)
        :param list args: positional args for the interaction
        :param dict kwargs: kwargs for the interaction

        :rtype: gevent.AsyncResult
        :returns: -- a :class:`gevent.AsyncResult` that will hold the result of the interaction once it finished. When `partial_txn = True` it will return a dict that will hold the result, the connection, and the cursor that ran the transaction. (use for locking with SELECT FOR UPDATE)
        """

        async_result = AsyncResult()
        if is_write:
            use_pool = self.default_write_pool if pool is None else pool
        else:
            use_pool = self.default_read_pool if pool is None else pool

        if isinstance( interaction, FunctionType ) or isinstance( interaction, MethodType ):
            def wrapped_transaction_f( async_res, interaction, conn = None,
                                       cursor = None, *args ):
                try:
                    if not conn:
                        conn = self.conn_pools[ use_pool ].get()
                    kwargs[ 'conn' ] = conn
                    if cursor:
                        kwargs[ 'cursor' ] = cursor
                    elif 'cursor' in getargspec( interaction )[ 0 ]:
                        kwargs[ 'cursor' ] = kwargs[ 'conn' ].cursor()
                    res = interaction( *args, **kwargs )
                    if not partial_txn:
                        async_res.set( res )
                        if cursor and not cursor.closed:
                            cursor.close()
                    else:
                        async_res.set( { 'result': res,
                                         'connection': conn,
                                         'cursor': kwargs[ 'cursor' ] } )
                except DatabaseError, e:
                    if self.do_log:
                        self.logger.info( "exception: %s", ( e, ) )
                    async_result.set_exception( DBInteractionException( e ) )
                except Exception, e:
                    if self.do_log:
                        self.logger.info( "exception: %s", ( e, ) )
                    async_result.set_exception( DBInteractionException( e ) )
                finally:
                    if conn and not partial_txn:
                        self.conn_pools[ use_pool ].put( conn )

            gevent.spawn( wrapped_transaction_f, async_result, interaction,
                          conn = conn, cursor = cursor, *args )
            return async_result

        elif isinstance( interaction, StringType ):
            def transaction_f( async_res, sql, conn = None, cursor = None,
                               *args ):
                try:
                    if not conn:
                        conn = self.conn_pools[ use_pool ].get()
                    if not cursor:
                        cursor = conn.cursor()
                    if not dry_run:
                        if interaction_args is not None:
                            cursor.execute( sql, interaction_args )
                        else:
                            cursor.execute( sql )
                        if get_result:
                            res = cursor.fetchall()
                        else:
                            res = True
                        if is_write and not partial_txn:
                            conn.commit()
                    else:
                        res = cursor.mogrify( sql, interaction_args )
                    if not partial_txn:
                        cursor.close()
                        async_res.set( res )
                    else:
                        async_res.set( { 'result': res,
                                         'connection': conn,
                                         'cursor': cursor} )
                except DatabaseError, e:
                    if self.do_log:
                        self.logger.info( "exception: %s", ( e, ) )
                    async_result.set_exception( DBInteractionException( e ) )
                except Exception, e:
                    traceback.print_exc( file = sys.stdout )
                    # if is_write and partial_txn: # ??
                    conn.rollback()
                    if self.do_log:
                        self.logger.info( "exception: %s", ( e, ) )
                    async_result.set_exception( DBInteractionException( e ) )
                finally:
                    if conn and not partial_txn:
                        self.conn_pools[ use_pool ].put( conn )

            gevent.spawn( transaction_f, async_result, interaction,
                          conn = conn, cursor = cursor, *args )
            return async_result
        else:
            raise DBInteractionException( "%s cannot be run. run() only accepts FunctionTypes, MethodType, and StringTypes" % interacetion )

    def listen_on( self, result_queue = None, channel_name = None, pool = None,
                   cancel_event = None, sleep_cycle = 0.1 ):
        """
        Listen for asynchronous events on a named Channel and pass them to the result_queue

        :param gevent.Queue result_queue: The :class:`gevent.Queue` to pass event payloads to
        :param string channel_name: Name of the channel to LISTEN on
        :param string pool: Name of the pool to get the connection from
        :param gevent.Event cancel_event: A :class:`gevent.Event` which will break the listening loop when set
        """

        if self.db_module != 'psycopg2':
            raise DBInteractionException( "This feature requires PostgreSQL 9.x." )
        use_pool = self.default_write_pool if pool is None else pool
        try:
            def start_listener():
                self.active_listeners[ channel_name ] = PGChannelListener( result_queue, self.conn_pools[ use_pool ], channel_name )

            # do we need a listen loop for all PGChannelListeners? maybe one is enough...
            def listen( result_queue, cancel_event ):
                while 1:
                    if cancel_event.is_set():
                        self.active_listeners[ channel_name ].unregister_queue( id( result_queue ) )
                        if self.do_log:
                            self.logger.info( "stopped listening on: %s", ( channel_name, ) )
                        break
                    gevent.sleep( sleep_cycle )

            listener_jobs = [ gevent.spawn( start_listener ),
                              gevent.spawn( listen, result_queue, cancel_event ) ]
            gevent.joinall( listener_jobs )
        except Exception, e:
            print "# FRAKK", e
            if self.do_log:
                self.logger.info( e )



# TODO: make this an option...?
# DEC2FLOAT = psycopg2.extensions.new_type(
#     psycopg2.extensions.DECIMAL.values,
#     'DEC2FLOAT',
#     lambda value, curs: float( value ) if value is not None else None )
# psycopg2.extensions.register_type( DEC2FLOAT )
