SAFe Python Tools
=================

The safepy package provides a set of tools and utilities useful for
interacting with SAFe from python.

Talking to Products
-------------------

The :mod:`safepy.api` library provides a quickly and easy way of
getting access to a remote product. It fetches the SAFe specification
file and dynamically creates a set of classes to bridge the SAFe
object model with a Python one. ::

    >>> import safepy
    >>> api = safepy.api('example-profile')

The resulting api object gives us a well typed window into the product
of interest. For example, we can look at sip profiles.

.. note::
   The SAFe object module routinely uses characters which are not
   valid for python typenames. For example, :code:`sip-ip` and
   :code:`TLS/tls-sip-port`. The API builder works around this by
   exposing a sanantized version of these names. All invalid
   characters are replaced with underscores.

::

    >>> my_profile = api.sip.profile['my_profile']
    >>> my_profile.sip_ip
    u'eth0'
    >>> my_profile.TLS_tls_sip_port
    u'5061'

And we're able to do the full rage of operations, create, delete,
list, update and retrieve. ::

    >>> my_profile.limit()
    []
    >>> my_profile.create('example-limit', {'method': 'REGISTER', 'limit': 5, 'period': 60})
    >>> my_profile.limit.list()
    [u'example-limit']
    >>> my_profile.limit['example-limit'].retrieve()
    {'method': 'REGISTER', 'limit': 5, 'period': 60}

Parsing the SAFe Specification
------------------------------

To be able to this dynamic generation, the SAFe specification file
first has to be parsed, done in :mod:`safepy.parser`. The parser pulls
the specification through REST and builds an ast tree representing the
specification.

The separated parsing step allows us to handle all inconsistencies and
errors in the specification in one place, allowing for a simpler api
builder that works across multiple product versions without it needing
any product specific workarounds.

This library is exposed so other potentially interesting applications
of the specification file can be done without needing to write their
own parser. ::

    >>> ast = safepy.parse('example-profile')
    [ObjectNode(tag=firewall, cls=[], methods=[], objs=[ObjectNode(tag=service, ...

API Reference
-------------

The API reference (generated from the *docstrings* within the library)
covers all the exposed APIs of this library.

.. toctree::
   :maxdepth: 2

   api/api
   api/parser
   api/url
