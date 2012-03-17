# -*- coding: utf-8 -*-

# Copyright 2011-2012 Florian von Bock (f at vonbock dot info)
#
# gDBPool - db connection pooling for gevent

__author__ = "Florian von Bock"
__email__ = "f at vonbock dot info"
__version__ = "0.1.3"


import gevent
from gevent import monkey; monkey.patch_all()

import psycopg2
import sys, traceback

from psyco_ge import make_psycopg_green; make_psycopg_green()
assert 'gdbpool.psyco_ge' in sys.modules.keys()
from psycopg2.extras import RealDictCursor
from time import time

from gdbpool_error import PoolConnectionException


class PoolConnection( object ):
    """
    Single connection object for the pool

    On object initialization the object initializes the DB connection
    (a standard Db-API connection object).
    Direct access to the object is only possible when the member name
    is prefixed with "PoolConnection\_". Otherwise member access goes
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
            raise PoolConnectionException( "PoolConnection failed: Could not connect to database: %s" % e )

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
        # deprecated
        #elif self.PoolConnection_db_module_name == 'MySQLdb':
        #    args.append( MySQLdb.cursors.DictCursor if self.PoolConnection_cursor_type is None else self.PoolConnection_cursor_type )
        #    return self.PoolConnection_conn.cursor( *args, **kwargs )


