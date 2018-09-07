==============================================
gDBPool: Postgres database pooling with gevent
==============================================

gDBPool is a library to do async communication to `PostgreSQL
<http://postgresql.org>`_ using `psycopg2 <http://initd.org/psycopg/>`_ and gevent.

Please refer to the `full gDBPool documenation <https://vonbock.info/software/gdbpool/documentation/>`_ for more information.

Any help testing/breaking things and then leaving an issue on github is greatly appreciated!

If you have any questions, ping me on twitter `@fvbock <https://twitter.com/fvbock>`_.


.. end-summary

.. _requirements:

Requirements
------------

General
^^^^^^^

* Python 2.7
* Postgres 9.0.x+

Via Pip
^^^^^^^

* gevent 0.13.6+ - also tested with the 1.0 alpha/beta versions
* psycopg 2.4.2+


Installation
------------

install the required packages ::

    $ pip install -r requirements.txt

then install the package itself ::

    $ sudo python setup.py install



