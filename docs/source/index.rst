.. gDBPool documentation master file, created by
   sphinx-quickstart on Sun Feb  5 16:53:36 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. highlight:: python
.. currentmodule:: gDBPool

===========================================================================
gDBPool - asynchronous database interaction pooling for gevent and Postgres
===========================================================================

gDBPool is a gevent and postgres based library providing interaction and connection pooling.
The original motivation to build gDBPool was to implement a connection pool for gevent. With gevent being an asynchronous networking library, and having `Postgres asynchronous event capabilities <http://initd.org/psycopg/docs/advanced.html#asynchronous-notifications>`_ with `LISTEN <http://www.postgresql.org/docs/9.1/static/sql-listen.html>`_ and `NOTIFY <http://www.postgresql.org/docs/9.1/static/sql-notify.html>`_ building support for it was pretty much natural. Of course this makes the library bound to Postgres and psycopg2, but for now that is fine.
The initial version had support for the use of different DB-API libraries for the non async features but support has been dropped for now.

gDBPool features
----------------

* multiple connection pool support (including read-only/write pool distinction)
* running plain SQL queries as well as more complex transactions that are encapsulated in a function or method
* partial transaction execution (ie. to run an interaction that obtains a row level lock, and then - maybe after some other operations - run a second interaction that uses that lock and in the end commits the transaction).
* ayncronous notification/event support (postgres LISTEN/NOTIFY)

Contents:

.. toctree::
   :maxdepth: 5

   classes/index

.. include:: ../../README.rst
    :start-after: end-summary


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

