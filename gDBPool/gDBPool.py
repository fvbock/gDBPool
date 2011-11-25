# -*- coding: utf-8 -*-

# Copyright 2011 Florian von Bock (f at vonbock dot info)
#
# gDBPool - db connection pooling for gevent

__author__ = "Florian von Bock"
__email__ = "f at vonbock dot info"
__version__ = "0.1.1"


import gevent
from gevent import monkey; monkey.patch_all()

import psycopg2
import sys

from psyco_ge import make_psycopg_green; make_psycopg_green()
assert 'psyco_ge' in sys.modules.keys()

from gevent.queue import Queue
from gevent.queue import Empty as QueueEmptyException
from gevent.pool import Pool as GreenPool
from gevent.event import AsyncResult
from time import time
from types import FunctionType, StringType
from gDBPoolError import DBInteractionException, DBPoolConnectionException, PoolConnectionException, StreamEndException
from PGChannelListener import PGChannelListener
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT, ISOLATION_LEVEL_READ_COMMITTED
psycopg2.extensions.register_type( psycopg2.extensions.UNICODE )
psycopg2.extensions.register_type( psycopg2.extensions.UNICODEARRAY )

# TODO: make this an option...
# DEC2FLOAT = psycopg2.extensions.new_type(
#     psycopg2.extensions.DECIMAL.values,
#     'DEC2FLOAT',
#     lambda value, curs: float( value ) if value is not None else None )
# psycopg2.extensions.register_type( DEC2FLOAT )


class DBInteractionPool( object ):
    """ The DBInteractionPool can manages `DBConnectionPool` instances and can run
        queries or functions (ie. several queries wrapped in a function) on one of
        these pools.

        If you want logging pass `do_log = True` to the constructor.
    """
    def __new__( cls, dsn, *args, **kwargs ):
        if not hasattr( cls, '_instance' ):
            cls._instance = object.__new__( cls )
        return cls._instance

    def __init__( self, dsn, pool_size = 10, pool_name = 'default',
                  db_module = 'psycopg2', do_log = False, *args, **kwargs ):
        if do_log == True:
            import logging
            logging.basicConfig( level = logging.INFO, format = "%(asctime)s %(message)s" )
            self.logger = logging.getLogger()
        self.do_log = do_log
        self.request_queue = Queue( maxsize = None )
        self.db_module = db_module
        self.conn_pools = {}
        self.default_write_pool = None
        self.default_read_pool = None
        self.default_pool = None
        self.add_pool( dsn = dsn, pool_name = 'default', pool_size = pool_size,
                       default_write_pool = True, default_read_pool = True,
                       db_module = self.db_module )

    def __del__( self ):
        if self.do_log == True:
            self.logger.info( "__del__ DBInteractionPool" )
        for p in self.conn_pools:
            p.__del__()

    # def __call__( self, txn_f ):
    #     def wrapped_f_call( *args, **kwargs ):
    #         return self.run( txn_f, *args, **kwargs  )
    #     return wrapped_f_call

    def add_pool( self, dsn = None, pool_name = None, pool_size = 10,
                  default_write_pool = False, default_read_pool = False,
                  default_pool = False, db_module = 'psycopg2' ):
        if not self.conn_pools.has_key( pool_name ):
            self.conn_pools[ pool_name ] = DBConnectionPool( dsn, db_module = self.db_module,
                                                             pool_size = pool_size, do_log = self.do_log )
            if default_write_pool == True:
                self.default_write_pool = pool_name
                if self.default_pool == True or self.default_pool is None:
                    self.default_pool = pool_name
            if default_read_pool == True:
                self.default_read_pool = pool_name
        else:
            raise DBInteractionException( "Already have a pool with the name: %s. ConnectionPool not added!" % ( pool_name, ) )

    @property
    def pool( self ):
        return self.conn_pools[ self.default_pool ]

    def run( self, interaction = None, interaction_args = None, get_result = True,
             is_write = True, pool = None, dry_run = False, *args, **kwargs ):
        async_result = AsyncResult()
        if is_write == True:
            use_pool = self.default_write_pool if pool is None else pool
        else:
            use_pool = self.default_read_pool if pool is None else pool

        if isinstance( interaction, FunctionType ):
            def wrapped_transaction_f( async_res, interaction, *args ):
                try:
                    conn = self.conn_pools[ use_pool ].get()
                    kwargs[ 'conn' ] = conn
                    res = interaction( *args, **kwargs )
                    self.conn_pools[ use_pool ].put( conn )
                    async_res.set( res )
                except Exception, e:
                    if self.do_log == True:
                        self.logger.info( "exception: %s", ( e.message, ) )
                    async_result.set_exception( DBInteractionException( e.message ) )

            gevent.spawn( wrapped_transaction_f, async_result, interaction, *args )
            return async_result

        if isinstance( interaction, StringType ):
            def transaction_f( async_res, sql, *args ):
                try:
                    conn = self.conn_pools[ use_pool ].get()
                    cur = conn.cursor()
                    if interaction_args is not None:
                        cur.execute( sql, interaction_args )
                    else:
                        cur.execute( sql )
                    if get_result:
                        res = cur.fetchall()
                    else:
                        res = True
                    if is_write:
                        conn.commit()
                    cur.close()
                    self.conn_pools[ use_pool ].put( conn )
                    async_res.set( res )
                except Exception, e:
                    if is_write:
                        conn.rollback()
                    if self.do_log == True:
                        self.logger.info( "exception: %s", ( e.message, ) )
                    async_result.set_exception( DBInteractionException( e.message ) )

            gevent.spawn( transaction_f, async_result, interaction, *args )
            return async_result

    def listen_on( self, result_queue = None, channel_name = None, pool = None,
                   timeout = None, cancel_event = None ):
        if self.db_module != 'psycopg2':
            raise DBInteractionException( "This feature requires PostgreSQL 9.x." )
        use_pool = self.default_write_pool if pool is None else pool
        try:
            conn = self.conn_pools[ use_pool ].get( auto_commit = True )
            q = Queue( maxsize = None )
            listener = PGChannelListener( q, conn, channel_name )
            while 1:
                if cancel_event.is_set():
                    print "stop event received"
                    break
                try:
                    result_queue.put( q.get_nowait() )
                except QueueEmptyException:
                    gevent.sleep( 0.001 )
        except Exception, e:
            if self.do_log == True:
                self.logger.info( e )
            print e

        if self.do_log == True:
            self.logger.info( "stopped listening on: %s", ( channel_name, ) )
        listener.unregister_queue( id( q ) )
        self.conn_pools[ use_pool ].put( conn )
        self.logger.info( "done listening" )


class DBConnectionPool( object ):
    """ The Connection Pool

        The pool takes a DSN, the name of the database module (default: psycopg2),
        the pool size and the minimal connection life time as initialization arguments.
        The DNS is the only mandatory argument.
        If you want logging pass `do_log = True` to the constructor.

        The pool provides 2 main functions: get() and put()
    """
    def __init__( self, dsn, db_module = 'psycopg2', pool_size = 10, conn_lifetime = 600, do_log = False ):
        if do_log == True:
            import logging
            logging.basicConfig( level = logging.INFO, format = "%(asctime)s %(message)s" )
            self.logger = logging.getLogger()
        self.do_log = do_log
        self.dsn = dsn
        self.db_module = db_module
        self.pool_size = pool_size
        self.CONN_RECYCLE_AFTER = conn_lifetime if conn_lifetime is not None else 0
        self.pool = Queue( self.pool_size )
        __import__( db_module )
        self.connection_jobs = map( lambda x: gevent.spawn( self.create_connection ), xrange( self.pool_size ) )
        try:
            gevent.joinall( self.connection_jobs, timeout = 10 )
            assert self.pool_size == self.pool.qsize()
            if self.do_log == True:
                self.logger.info( "$ poolsize: %i" % self.pool.qsize() )
            self.ready = True
        except Exception, e:
            raise PoolConnectionException( e.message )

    def __del__( self ):
        while not self.pool.empty():
            conn = self.pool.get()
            conn.close()

    def create_connection( self ):
        self.pool.put( PoolConnection( self.db_module, self.dsn ) )

    def get( self, timeout = None, auto_commit = False ):
        try:
            conn = self.pool.get( timeout = timeout )
            if auto_commit and self.db_module == 'psycopg2':
                conn.set_isolation_level( ISOLATION_LEVEL_AUTOCOMMIT )
            return conn
        except gevent.queue.Empty, e:
            raise PoolConnectionException( e.message )

    def put( self, conn, timeout = 1 ):
        if isinstance( conn, PoolConnection ):
            if self.CONN_RECYCLE_AFTER != 0 and time() - conn.PoolConnection_initialized_at < self.CONN_RECYCLE_AFTER:
                try:
                    if conn.isolation_level == ISOLATION_LEVEL_READ_COMMITTED:
                        conn.set_isolation_level( ISOLATION_LEVEL_READ_COMMITTED )
                        conn.commit()
                    self.pool.put( conn, timeout = timeout )
                except gevent.queue.Full, e:
                    raise PoolConnectionException( e.message )
            else:
                if self.do_log == True:
                    self.logger.debug( "recycling conn." )
                conn.close()
                del conn
                g = gevent.spawn( self.create_connection )
                g.join()
        else:
            raise PoolConnectionException( "Passed object %s is not a PoolConnection." % ( conn, ) )

    @property
    def qsize( self ):
        return self.pool.qsize()

    @property
    def is_ready( self ):
        return self.ready == True



class PoolConnection( object ):
    """ Single connection object for the pool

        On object initialization the object initializes the DB connection.
        Direct access to the object is only possible when the member name
        is prefixed with 'PoolConnection_'. Otherwise member access goes
        to the 'inner' connection object.

    """
    def __init__( self, db_module, dsn, cursor_type = None ):
        self.db_module_name = db_module
        self.cursor_type = cursor_type
        self.db_module = sys.modules[ db_module ]
        try:
            self.conn = self.PoolConnection_db_module.connect( dsn )
            self.initialized_at = time()
        except Exception, e:
            raise PoolConnectionException( e.message )

    def __getattribute__( self, name ):
        if name.startswith( 'PoolConnection_' ) or name == 'cursor':
            if name == 'cursor':
                return object.__getattribute__( self, name )
            else:
                return object.__getattribute__( self, name[15:] )
        else:
            return object.__getattribute__( self.PoolConnection_conn, name )

    def cursor( self, *args, **kwargs ):
        if self.PoolConnection_db_module_name == 'psycopg2':
            kwargs[ 'cursor_factory' ] = RealDictCursor if self.PoolConnection_cursor_type is None else self.PoolConnection_cursor_type
            return self.PoolConnection_conn.cursor( *args, **kwargs )
        elif self.PoolConnection_db_module_name == 'MySQLdb':
            args.append( MySQLdb.cursors.DictCursor if self.PoolConnection_cursor_type is None else self.PoolConnection_cursor_type )
            return self.PoolConnection_conn.cursor( *args, **kwargs )


