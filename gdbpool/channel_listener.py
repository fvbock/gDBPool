# -*- coding: utf-8 -*-

# Copyright 2011-2012 Florian von Bock (f at vonbock dot info)
#
# gDBPool - db connection pooling for gevent
#
# PGChannelListener - subscribes to a (NOTIFY) channel on postgres
# via LISTEN and streams the events to the subscribes result_queues

__author__ = "Florian von Bock"
__email__ = "f at vonbock dot info"
__version__ = "0.1.3"


import gevent
from gevent import monkey; monkey.patch_all()
from psyco_ge import make_psycopg_green; make_psycopg_green()

import psycopg2

from gevent.select import select
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


class PGChannelListenerException( Exception ):
    pass


def pipe_colon_unmarshall( payload_string ):
    """
    Convert a pipe seperated string of <key:value> pairs as a dict

    :param string payload_string:
    :returns: dict -- unmarshalled NOTIFY data
    """

    payload_data = {}
    try:
        for kv_pair in payload_string.split( '|' ):
            k, v = kv_pair.split( ':', 1 )
            payload_data[ k ] = v
    except Exception, e:
        raise PGChannelListenerException( "Unmarshalling of the LISTEN payload failed: %s" % ( e.message, ) )
    return payload_data


class PGChannelListener( object ):
    """
    A Listener for Postgres LISTEN/NOTIFY channels using gevent.

    For each channel there will be one `:class:PGChannelListener` instance that fans
    notifications out to the subscribed `:class:Queue`}
    """

    def __new__(  cls, q, pool, channel_name, *args, **kwargs ):
        if not hasattr( cls, '_instances' ):
            cls._instances = {}
        spawn = False
        if not cls._instances.has_key( channel_name ):
            cls._instances[ channel_name ] = object.__new__( cls )
            cls._instances[ channel_name ].subscribers = {}
            cls._instances[ channel_name ].pool = pool
            cls._instances[ channel_name ].conn = pool.get( iso_level = ISOLATION_LEVEL_AUTOCOMMIT )
            cls._instances[ channel_name ].cur = None
            cls._instances[ channel_name ].channel_name = channel_name
            spawn = True

        # hai hai... using id for this kind of stuff is sort of dangerous.
        # will come up with something less pointing gun at foot(TM). later. (TM).
        cls._instances[ channel_name ].subscribers[ id( q ) ] = q
        if spawn:
            gevent.spawn( cls._instances[ channel_name ].listen ).join()
        return cls._instances[ channel_name ]

    def __init__( self, q, pool, channel_name ):
        """
        Create a Listener for a channel_name and pass the notifications to q result `Queue`.

        :param gevent.Queue q: Queue to pass asynchronous payloads to
        :param gDBPool.DBConnectionPool pool: Connection pool to get a connection from and execute ``LISTEN <channel_name>;`` on if no other instance listens on that channel already. In the latter case the q is just being subscribed to the channel.
        :param string channel_name: channel to listen on. (``LISTEN <channel_name>;``)

        :returns: -- PGChannelListener instance
        """

        pass

    def __del__( self ):
        print "** __del__", self.channel_name
        del PGChannelListener._instances[ self.channel_name ]

    def unregister_queue( self, q_id ):
        """
        Unregister a Queue from its channel.

        If it was the last subscriber stop listening on the channel and put the connection used back onto the pool.

        :param q_id: The id() of the Queue to be unsubscribed from the channel
        """

        if self.stop_event.is_set():
            return
        del self.subscribers[ q_id ]
        if len( self.subscribers ) == 0:
            self.stop_event.set()
            self.cur.close()
            self.pool.put( self.conn )

    def listen( self, unmarshaller = pipe_colon_unmarshall ):
        """
        Subscriber to the channel and send notification payloads to the
        results Queue.

        :param function unmarshaller: Function to pass the `notify.payload` string into for unmarshalling into python object (ie. dict) data
        """

        self.stop_event = stop_event = gevent.event.Event()
        self.cur = self.conn.cursor()
        self.cur.execute( "LISTEN %s;" % ( self.channel_name, ) )
        while 1:
            if self.stop_event.is_set():
                return
            # TODO: test select with timeout and try/except
            # maybe try to listen on all channels with just one connection with short timeouts on the select
            # and then cycle through...
            if select( [ self.conn ], [], [] ) == ( [], [], [] ):
                print "LISTEN timeout."
            else:
                if self.stop_event.is_set():
                    return
                self.conn.poll()
                while self.conn.notifies:
                    if self.stop_event.is_set():
                        return
                    notify = self.conn.notifies.pop()
                    payload_data = unmarshaller( notify.payload )
                    for q_id in self.subscribers.iterkeys():
                        self.subscribers[ q_id ].put( payload_data )

