# -*- coding: utf-8 -*-

# Copyright 2011 Florian von Bock (f at vonbock dot info)
#
# gDBPool - Tests

__author__ = "Florian von Bock"
__email__ = "f at vonbock dot info"
__version__ = "0.1.1"


import gevent
from gevent import monkey; monkey.patch_all()

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


class gDBPoolTests( unittest.TestCase ):

    def setUp( self ):
        dsn = "host=127.0.0.1 port=5432 user=postgres dbname=gdbpool_test"
        dsn_read = "host=127.0.0.1 port=5433 user=postgres dbname=gdbpool_test"
        self.ipool = DBInteractionPool( dsn, pool_size = 16, do_log = True )
        # self.ipool_read = DBInteractionPool( dsn_read, pool_size = 16, do_log = True )

    def tearDown( self ):
        del( self.ipool )
        # del( self.ipool_read )

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
        """ Test running an invalid SQL interactions on the DBInteractionPool
        """

        sql = """
        SELECT val1, count(id) FROM test_values WHERE val2 %s GROUP BY val1 order by val1;
        """

        with self.assertRaises( DBInteractionException ):
            res = self.ipool.run( sql )
            print res.get()

    def test_select_ip_query( self ):
        """ Test running a bunch of random queries as SQL interactions on the
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

        logger.info( ' *** Start Interaction...' )
        res = self.ipool.run( interaction )
        res.get()
        # logger.info( res.get() )


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
            logger.info( "+++ " + repr( res.get().get() ) )

        greenlets = []
        for i in xrange( 5 ):
            greenlets.append( gevent.spawn( self.ipool.run, interaction ) )
            greenlets[ i ].link( print_res )
        gevent.joinall( greenlets, timeout = 10, raise_error = True )


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
            print "#START"
            import time
            while 1:
                st = time.time()
                if runtime > 4.0:
                    print "#RT OVER STOP"
                    break
                try:
                    notify = rq.get_nowait()
                    print notify
                except QueueEmptyException:
                    gevent.sleep( 0.01 )

                tt = time.time() - st
                runtime += tt

            print "#STOP"
            stop_event.set()

        for i in xrange( 10 ):
            gevent.spawn( listen )

        greenlets = []
        for i in xrange( 5 ):
            greenlets.append( gevent.spawn( run_insert, i ) )
            greenlets.append( gevent.spawn( run_update, i ) )
        gevent.joinall( greenlets )



test_suite = unittest.TestLoader().loadTestsFromTestCase( gDBPoolTests )
unittest.TextTestRunner( verbosity = 1 ).run( test_suite )
