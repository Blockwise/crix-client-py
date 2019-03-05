.. crix documentation master file, created by
   sphinx-quickstart on Tue Mar  5 14:20:29 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to crix's documentation!
================================



This official client of CRIX.io crypto exchange.

Environment requirements:

* python 3.5+
* requests 2.*

For several operations like create/cancel orders you should
also be registered in the exchange and got BOT API token and secret.

To access historical data you should get explicit permission by exchange support.

Installation
------------

- over pip: ``pip install crix``
- manually: ``pip install git+https://github.com/blockwise/crix-client-py.git#egg=crix``

Rate limit
----------

Currently for BOT API there is a rate limit about 100 requests/second, however several functions in the library
can use multiple requests inside as noted in their documentation.

Sample usage
------------


Unauthorized (public) access
^^^^^^^^^^^^^^^^^^^^^^^^^^^^


.. code-block:: python

   import crix

   client = crix.Client(env='prod')

   # get all symbols
   for symbol in client.fetch_markets():
       print(symbol)

   # get some order book
   depth = client.fetch_order_book('BTC_BCH')
   print(depth)


Authorized (clients-only) access
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. warning::

   **BOT API token and secret are required and should be obtained for each client from the exchange**


.. code-block:: python

   import crix
   from crix.models import NewOrder

   client = crix.AuthorizedClient(
       env='prod',
       token='xxyyzz',
       secret='aabbcc'
   ) # replace token and secret value for your personal API credentials


   # list all open orders
   for order in client.fetch_open_orders('BTC_BCH'):
       print(order)

   # prepare order
   new_order = NewOrder.market('BTC_BCH', is_buy=True, quantity=0.1) # or use NewOrder constructor
   # place order
   order = client.create_order(new_order)
   print(order)



.. toctree::
   :maxdepth: 2
   :caption: Contents:

   clients.rst
   models.rst

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

