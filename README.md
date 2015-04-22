# safepy

Python library that auto-generates generates a wrapper around NSC's
REST API. The NSC webui provides a specification file describing its
exposed functionality and this library reads it, parses it, and
generates a set of classes wrapping that functionality to expose it to
python.

## Talking to Products

The `safepy.api` library provides a quickly and easy way of getting
access to a remote product. It fetches the specification file from the
device and uses it to dynamically generates a wrapper around the
described documentation. Care it taken to try and attach documentation
to `__doc__` fields where it's provided, so the resulting wrapper
should be fairly well documented internally.

```lang=python
>>> import safepy
>>> api = safepy.api('example-profile')
```

The resulting `api` object gives us a window into the product of
interest.

## Examples

### Creating a profile

There are two required fields for creating a new sip profile: `sip-ip`
and `sip-port`. The `sip-ip` field has to be the name of the ip
object, so first we have to find it:

```
>>> sip_ip = api.network.ip.list({'address': '198.51.100.5'})
>>> sip_ip
[u'ip_3']
```

Then we feed this information to create a new profile:

```lang=python
>>> profile = api.sip.profile.create('example', {'sip-ip': sip_ip[0],
...                                              'sip-port': 5080})
```

Remember to apply changes (see below) when done.

### Listing all profiles

Listing profiles is simple:

```lang=python
>>> api.sip.profile.list()
[u'example-profile']
```

### Applying changes

TODO

## Roadmap

TODO
