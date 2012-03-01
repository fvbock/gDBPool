gDBPool Usage
*************

Class Documentation
===================

.. module:: gDBPool

* :doc:`interaction_pool`: Manages one or more :class:`connection_pool.DBConnectionPool`, can seperate between *read only* (no sideeffects) and write pools. On this pool interactions (functions/methods that take a connection and cursor as arguments or plain SQL queries passed as `string`) can be executed asynchronously.

* :doc:`connection_pool`: A pool of :class:`pool_connection.PoolConnection` to one databases that provides get() and put() methods (for connections) and handles connection recyling

* :doc:`pool_connection`: Wrapper class for DB-API connection objects that adds a couple of internals used by the :class:`connection_pool.DBConnectionPool`.



* :doc:`channel_listener`: The DBInteractionPool ()


Quick tests/examples
====================

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

now you can create a :class:`interaction_pool.DBInteractionPool` instance:

.. code-block:: python

    dsn = "host=127.0.0.1 port=5432 user=postgres dbname=gdbpool_test"
    ipool = DBInteractionPool( dsn, pool_size = 16, do_log = True )


.. toctree::
    :glob:
    :hidden:

    /classes/*
