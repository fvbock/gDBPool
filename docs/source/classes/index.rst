Class Documentation
-------------------

.. module:: gDBPool

* :doc:`/classes/interaction_pool`: Manages one or more :class:`connection_pool.DBConnectionPool`, can seperate between *read only* (no sideeffects) and write pools. On this pool interactions (functions/methods that take a connection and cursor as arguments or plain SQL queries passed as `string`) can be executed asynchronously.

* :doc:`/classes/connection_pool`: A pool of :class:`pool_connection.PoolConnection` to one databases that provides get() and put() methods (for connections) and handles connection recyling

* :doc:`/classes/pool_connection`: Wrapper class for DB-API connection objects that adds a couple of internals used by the :class:`connection_pool.DBConnectionPool`.

* :doc:`/classes/channel_listener`: The DBInteractionPool ()


.. toctree::
    :glob:
    :hidden:

    /classes/*
