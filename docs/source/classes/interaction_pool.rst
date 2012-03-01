=================
DBInteractionPool
=================

While the DBConnectionPool resembles a simple, *"classic"* connection pool, the DBInteractionPool is sort of a meta or management pool of one or more :class:`DBConnectionPool` instances.

The idea behind this structure is to support master slave replicated database cluster backends that manage write and read-only (without side-effects) operations on different machines/clusters.

DBInteractionPool provides two main methods for interaction:

* :meth:`DBInteractionPool.run` to run queries (interactions) on the pool

* :meth:`DBInteractionPool.listen` to subscribe to asyncronous event channels from the database



Object Documenation
-------------------

.. autoclass:: gdbpool.interaction_pool.DBInteractionPool
   :members:
   :inherited-members:
   :private-members:
   :show-inheritance:



