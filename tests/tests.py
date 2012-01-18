# -*- coding: utf-8 -*-

# Copyright 2011-2012 Florian von Bock (f at vonbock dot info)
#
# gDBPool - Tests

__author__ = "Florian von Bock"
__email__ = "f at vonbock dot info"
__version__ = "0.1.2"


import gevent
from gevent import monkey; monkey.patch_all()

import os, sys
sys.path.insert( 0, os.path.dirname( __file__ ).rpartition( '/' )[ 0 ] )

import unittest
import random
import logging

from gevent.select import select
from gevent.queue import Queue
from gevent.queue import Empty as QueueEmptyException
from gDBPool.gDBPoolError import DBInteractionException, DBPoolConnectionException, PoolConnectionException, StreamEndException
from gDBPool.gDBPool import DBInteractionPool, DBConnectionPool, PoolConnection

logging.basicConfig( level = logging.INFO, format = "%(asctime)s %(message)s" )
logger = logging.getLogger()

dsn = "host=127.0.0.1 port=5432 user=postgres dbname=gdbpool_test"
#dsn_read = "host=127.0.0.1 port=5433 user=postgres dbname=gdbpool_test"


class gDBPoolTests( unittest.TestCase ):

    def setUp( self ):
        print "\n================================================================================\nRunning: %s\n================================================================================" % ( self._testMethodName )
        self.ipool = DBInteractionPool( dsn, pool_size = 16, do_log = True )

    def tearDown( self ):
        self.ipool.__del__()

    def test_connect_nonexisting_host_port( self ):
        with self.assertRaises( PoolConnectionException ):
            dsn = "host=127.0.0.1 port=6432 user=postgres dbname=gdbpool_test"
            fail_ipool = DBInteractionPool( dsn, pool_size = 1, do_log = False )

    def test_connect_nonexisting_db( self ):
        with self.assertRaises( PoolConnectionException ):
            dsn = "host=127.0.0.1 port=5432 user=postgres dbname=gdbpool_test_not_here"
            fail_ipool = DBInteractionPool( dsn, pool_size = 1, do_log = False )

    def test_connect_pool_size_too_big( self ):
        pass

    def test_invalid_query( self ):
        """Test running an invalid SQL interactions on the DBInteractionPool"""

        sql = """
        ESLECT val1, count(id) FROM test_values GROUP BY val1 order by val1;
        """

        with self.assertRaises( DBInteractionException ):
            res = self.ipool.run( sql )
            print res.get()

    def test_select_ip_query( self ):
        """
        Test running a bunch of random queries as SQL interactions on the
        DBInteractionPool
        """

        sql1 = """
        SELECT val1, count(id) FROM test_values WHERE val2 = %s GROUP BY val1 order by val1;
        """

        sql2 = """
        SELECT pg_sleep( %s );
        """

        sql3 = """
        SELECT val1, count(id) FROM test_values GROUP BY val1 order by val1;
        """

        import random
        from time import time
        greenlets = []

        def tests( val2 ):
            stt = time()
            ran = random.random()
            if ran <= 0.33:
                sql = sql1
                res = self.ipool.run( sql, [ val2 ] )
            elif ran <= 0.66:
                sql = sql2
                res = self.ipool.run( sql, [ 0.5 ] )
            else:
                sql = sql3
                res = self.ipool.run( sql )
            r = res.get()
            et = time()
            logger.info( r[0] )

        for i in xrange( 1, 10 ):
            greenlets.append( gevent.spawn( tests, i ) )

        gevent.joinall( greenlets, timeout = 10 )


    def test_select_ip_interaction( self ):
        def interaction( conn ):
            curs = conn.cursor()
            sql = """
            SELECT val1, val2, count(id) FROM test_values GROUP BY val1, val2 order by val1, val2;
            """
            curs.execute( sql )
            res = curs.fetchall()
            curs.close()
            return res

        res = self.ipool.run( interaction ).get()
        # logger.info( res )


    def test_select_ip_interactions( self ):
        def interaction( conn ):
            curs = conn.cursor()
            sql = """
            SELECT val1, count(id) FROM test_values GROUP BY val1 order by val1;
            """
            curs.execute( sql )
            res = curs.fetchall()
            curs.close()
            return res

        def print_res( res ):
            logger.info( "?" )
            while 1:
                try:
                    r = res.get().get_nowait()
                    logger.info( r )
                    break
                except gevent.Timeout:
                    gevent.sleep( 0.01 )


        greenlets = []
        for i in xrange( 5 ):
            greenlets.append( gevent.spawn( self.ipool.run, interaction ) )
            greenlets[ i ].link( print_res )
        gevent.joinall( greenlets, timeout = 10, raise_error = True )
        gevent.sleep( 1 )

    def test_listen_on( self ):
        def run_insert( wait ):
            gevent.sleep( 0.1 )
            sql = """
            INSERT INTO test_values ( val1, val2 ) VALUES ( %s, %s );
            SELECT pg_sleep( %s );
            """
            val1 = random.randint( 1, 10 )
            val2 = random.randint( 1, 100 )
            sleep_time = wait + random.random()
            res = self.ipool.run( sql, [ val1, val2, sleep_time ] )
            r = res.get()
            res.get()


        def run_update( wait ):
            gevent.sleep( 0.1 )
            sql = """
            UPDATE test_values SET val1 = 11, val2 = %s WHERE id = %s;
            SELECT pg_sleep( %s );
            """
            val2 = random.randint( 1, 100 )
            id = random.randint( 1, 1000000 )
            sleep_time = wait + random.random()
            res = self.ipool.run( sql, [ val2, id, sleep_time ] )
            r = res.get()

        def listen():
            runtime = 0.0
            rq = Queue( maxsize = None )
            stop_event = gevent.event.Event()
            gevent.spawn( self.ipool.listen_on, result_queue = rq, channel_name = 'notify_test_values', cancel_event = stop_event )
            import time
            while 1:
                st = time.time()
                if runtime > 5.0:
                    break
                try:
                    notify = rq.get_nowait()
                    print "NOTIFY", notify
                except QueueEmptyException:
                    gevent.sleep( 0.001 )

                tt = time.time() - st
                runtime += tt

            stop_event.set()
            gevent.sleep( 1 )

        for i in xrange( 5 ):
            gevent.spawn( listen )

        greenlets = []
        for i in xrange( 5 ):
            greenlets.append( gevent.spawn( run_insert, i ) )
            greenlets.append( gevent.spawn( run_update, i ) )
        gevent.joinall( greenlets )
        gevent.sleep( 1 )


    def test_partial_run( self ):
        def interaction_part1( conn, cursor ):
            # cursor = conn.cursor()
            sql = """
            SELECT * FROM test_values WHERE id = 20000 FOR UPDATE;
            """
            cursor.execute( sql )
            res = cursor.fetchone()
            return res

        # setting commit=false i want to get back not only the result, but also
        # the connection and cursor (that might hold any locks) as well
        txn_part1 = self.ipool.run( interaction_part1, partial_txn = True ).get()

        print "result from partial txn 1:", txn_part1
        data = txn_part1[ 'result' ]
        conn = txn_part1[ 'connection' ]
        cursor = txn_part1[ 'cursor' ]
        #TODO: do this inside the test - not manually
        print "try running:\nUPDATE test_values SET val2 = val2 + 100 WHERE id = %s;\nand check that the result will be %s. the current value for val2 is %s" % ( data[ 'id'], data[ 'val2' ] + 200, data[ 'val2'] )
        gevent.sleep( 5 )

        def interaction_part2( conn, cursor, pk, val2 ):
            try:
                sql = """
                UPDATE test_values SET val2 = %s WHERE id = %s;
                """
                cursor.execute( sql, [ val2, pk ] )
                res = cursor.fetchall()
                conn.commit()
            except Exception, e:
                res = e
                conn.rollback()

            return res

        txn_part2 = self.ipool.run( interaction_part2, conn = conn, cursor = cursor, pk = data[ 'id'], val2 = data[ 'val2'] + 100 ).get()
        print "result from partial txn 2:", txn_part2


test_suite = unittest.TestLoader().loadTestsFromTestCase( gDBPoolTests )
unittest.TextTestRunner( verbosity = 1 ).run( test_suite )
