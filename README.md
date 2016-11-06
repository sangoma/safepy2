# safepy2

[![Build Status](https://travis-ci.org/sangoma/safepy2.svg?branch=master)](https://travis-ci.org/sangoma/safepy2)

Python library that auto-generates generates a wrapper around NSC's
REST API. The NSC webui provides a specification file describing its
exposed functionality and this library reads it, parses it, and
generates a set of classes wrapping that functionality to expose it to
python.

This library is still very much a work-in-progress. While what's here
currently should be enough to do useful configuration of a product,
its much too low-level to be useful. Consumers of this API have to be
aware of low level details such as required fields, valid inputs, or
preconditions for certain operations (such as that a profile must be
stopped before it can be deleted) and the error messages when hitting
these cases will be unintuitive.

I want to grow a set of high-level wrappings that handle the
intricacies of profiles and trunks and dialplans instead of having to
rely on the low-level APIs.

Feel free to give feedback on the quality of api generation and/or the
wrappings.

## Talking to Products

The `safe.api` library provides a quickly and easy way of getting
access to a remote product. It fetches the specification file from the
device and uses it to dynamically generates a wrapper around the
described documentation. Care is taken to try and attach documentation
to `__doc__` fields where it's provided, so the resulting wrapper
should be fairly well documented internally.

~~~python
>>> import safe
>>> api = safe.api('10.10.9.100', token='A3553E08FB0DCCB80E4CE951666E16DE')
~~~

`token` is usually generated from the product's web interface under the
ReST API section. The resulting `api` object gives us a window into the
product of interest.

## Examples

### Creating a profile

There are two required fields for creating a new sip profile: `sip-ip`
and `sip-port`. The `sip-ip` field has to be the name of the ip
object, so first we have to find it:

~~~
>>> sip_ip = api.network.ip.search({'address': '198.51.100.5'})
>>> sip_ip
[u'ip_3']
~~~

Then we feed this information to create a new profile:

~~~python
>>> profile = api.sip.profile.create('example', {'sip-ip': sip_ip[0],
...                                              'sip-port': 5080})
~~~

Remember to apply changes (see below) when done.

### Listing all profiles

Listing profiles is simple:

~~~python
>>> list(api.sip.profile)
[u'example-profile']
~~~

Iteration is also supported.

### Accessing attributes of a profile

A getitem interface is exposed for fetching objects.

~~~python
>>> profile = api.sip.profile['example-profile']
>>> profile['sip-ip']
u'ip_3'
~~~

### Commiting changes

All the changes we've done thus far are staged without being applied.
Once we're all done, we still have to apply our changes to make them
live:

~~~python
>>> api.commit()
~~~

## Roadmap

TODO
