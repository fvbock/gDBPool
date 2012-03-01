# -*- coding: utf-8 -*-

# Copyright 2011-2012 Florian von Bock (f at vonbock dot info)
#
# gDBPool - db connection pooling for gevent

__author__ = "Florian von Bock"
__email__ = "f at vonbock dot info"
__version__ = "0.1.2"


import gevent
from gevent import monkey; monkey.patch_all()

import psycopg2
import sys, traceback

from psyco_ge import make_psycopg_green; make_psycopg_green()
assert 'gdbpool.psyco_ge' in sys.modules.keys()

from gevent.queue import Queue, Empty as QueueEmptyException
from time import time
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT, ISOLATION_LEVEL_READ_UNCOMMITTED, ISOLATION_LEVEL_READ_COMMITTED, ISOLATION_LEVEL_REPEATABLE_READ, ISOLATION_LEVEL_SERIALIZABLE
psycopg2.extensions.register_type( psycopg2.extensions.UNICODE )
psycopg2.extensions.register_type( psycopg2.extensions.UNICODEARRAY )
from psycopg2 import InterfaceError

from pool_connection import PoolConnection
from gdbpool_error import DBInteractionException, DBPoolConnectionException, PoolConnectionException, StreamEndException


class DBConnectionPool( object ):
    """
    The Connection Pool

    "Classic" pool of connections with connection lifecycle management
    """

    def __init__( self, dsn, db_module = 'psycopg2', pool_size = 10,
                  conn_lifetime = 600, do_log = False ):
        """
        :param string dsn: DSN for the default `class:DBConnectionPool`
        :param string db_module: name of the DB-API module to use
        :param int pool_size: Poolsize of the first/default `class:DBConnectionPool`
        :param int conn_lifetime: Number of seconds after which a connection will be recycled when :meth:`.put` back
        :param bool do_log: Log to the console or not
        """
        if do_log:
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
            if self.do_log:
                self.logger.info( "$ poolsize: %i" % self.pool.qsize() )
            self.ready = True
        except AssertionError, e:
            raise DBPoolConnectionException( "Could not get %s connections for the pool as requested. %s" % ( self.pool_size, e.message ) )
        except Exception, e:
            raise e

    def __del__( self ):
        while not self.pool.empty():
            conn = self.pool.get()
            conn.close()

    def create_connection( self ):
        """
        Try to open a new connection to the database and put it on the pool
        """
        try:
            self.pool.put( PoolConnection( self.db_module, self.dsn ) )
        except PoolConnectionException, e:
            raise e

    def get( self, timeout = None, iso_level = ISOLATION_LEVEL_READ_COMMITTED ):
        """
        Get a connection from the pool

        :param int timeout: seconds to wait for a connection or None
        :param iso_level: transaction isolation level to be set on the connection. Must be one of psycopg2.extensions ISOLATION_LEVEL_AUTOCOMMIT, ISOLATION_LEVEL_READ_UNCOMMITTED, ISOLATION_LEVEL_READ_COMMITTED, ISOLATION_LEVEL_REPEATABLE_READ, ISOLATION_LEVEL_SERIALIZABLE
        :returns: -- a :class:`PoolConnection`
        """
        try:
            conn = self.pool.get( timeout = timeout )
            if iso_level != ISOLATION_LEVEL_READ_COMMITTED:
                conn.set_isolation_level( iso_level )
            return conn
        except gevent.queue.Empty, e:
            raise PoolConnectionException( e )

    def put( self, conn, timeout = 1, force_recycle = False ):
        """
        Put a connection back onto the pool

        :param conn: The :class:`PoolConnection` object to be put back onto the pool
        :param int timeout: timeout in seconds to to put the connection onto the pool
        :param bool force_recycle: Force connection recycling independent from the pool wide connection lifecycle
        """
        if isinstance( conn, PoolConnection ):
            if ( self.CONN_RECYCLE_AFTER != 0 and time() - conn.PoolConnection_initialized_at < self.CONN_RECYCLE_AFTER ) and force_recycle == False:
                try:
                    conn.reset()
                    if conn.isolation_level != ISOLATION_LEVEL_READ_COMMITTED:
                        if self.do_log:
                            self.logger.info( "set ISOLATION_LEVEL_READ_COMMITTED." )
                        conn.set_isolation_level( ISOLATION_LEVEL_READ_COMMITTED )
                        conn.commit()
                    self.pool.put( conn, timeout = timeout )
                except gevent.queue.Full, e:
                    raise PoolConnectionException( e )
            else:
                if self.do_log:
                    self.logger.info( "recycling conn." )
                try:
                    conn.reset() # ?
                    conn.close()
                except InterfaceError:
                    pass
                del conn
                gevent.spawn( self.create_connection ).join()
        else:
            raise PoolConnectionException( "Passed object %s is not a PoolConnection." % ( conn, ) )

    @property
    def qsize( self ):
        return self.pool.qsize()
