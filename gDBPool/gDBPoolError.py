# -*- coding: utf-8 -*-

# Copyright 2011 Florian von Bock (f at vonbock dot info)
#
# gDBPool - db connection pooling for gevent
#
# Exceptions for the different gDBPool classes

__author__ = "Florian von Bock"
__email__ = "f at vonbock dot info"
__version__ = "0.1.1"


import sys, traceback


class DBPoolException( Exception ):
    def __init__( self, message ):
        Exception.__init__( self, message )
        # traceback.print_exc( file = sys.stdout )

class DBInteractionException( DBPoolException ):
    pass

class DBPoolConnectionException( DBPoolException ):
    pass

class PoolConnectionException( DBPoolException ):
    pass

class StreamEndException( DBPoolException ):
    pass
