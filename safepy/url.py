# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

# Copyright (C) 2014  Sangoma Technologies Corp.
# All Rights Reserved.
# Author(s)
# Simon Gomizelj <sgomizelj@sangoma.com>

'''Set of tools for dealing with and handling SAFe REST api urls.
A valid url takes the rough form of::

    /SAFe/sng_rest/<prefix>/<method>/<object path>

The api building defers object building to runtime, and since we don't
know the path or names of method until potentially really late, the
builder used to accumulate and store this information to render urls on
demand.
'''

import json
import requests
import urlparse


def unpack_rest_response(r):
    '''Interpret the response from a rest call. If we got an error,
    raise it. If not return either data or status, depending on
    availability'''

    r.raise_for_status()
    data = r.json()

    if 'error' in data:
        raise RuntimeError(data['error'])
    try:
        return data['data']
    except KeyError:
        return data['status']


class UrlBuilder(object):
    '''
    .. note::
       This class isn't intended to be constructed directly, use
       :func:`sangoma.safepy.url.url_builder` instead.

    Builder for SAFe REST api urls. A functional structure which stores
    a path and allows itself to be cloned to append more information.
    '''

    def __init__(self, base, *segments):
        self.base = base
        self.segments = segments

    def __call__(self, *segments):
        '''Create a new copy of the url builder with more segments
        appended to the new object builder.

        :param args: Any positional arguments for appending.
        '''

        segments = self.segments + segments
        return UrlBuilder(self.base, *segments)

    def url(self, prefix, method=None):
        '''Render a specific url to string.

        :param prefix: The prefix, for example, 'doc' or 'api'.
        :type prefix: str
        :param method: The optional method, if generating a method call.
        :type method: str
        '''
        prefix = (prefix, method) if method else (prefix,)
        segments = prefix + self.segments
        return urlparse.urljoin(self.base, '/'.join(segments))

    def get(self, prefix, method=None):
        url = self.url(prefix, method)
        return do_get(url)

    def post(self, prefix, method=None, data={}):
        url = self.url(prefix, method)
        headers = {'Content-Type': 'application/json'}
        return do_post(url, data)


def url_builder(host, port=80, scheme='http'):
    '''Construct a :class:`sangoma.safepy.url.UrlBuilder` to help build
    urls. Calculates a correct base for the url from the host, port and
    scheme.

    :param name: The hostname of the device of interest.
    :type name: str
    :param port: The port to use.
    :type port: int
    :param scheme: Specify the scheme of the request url.
    :type scheme: str
    :returns: A url builder for the hostname details.
    '''

    base = '{scheme}://{host}:{port}/SAFe/sng_rest/'.format(host=host,
                                                            port=port,
                                                            scheme=scheme)
    return UrlBuilder(base)


def get_docs(host, port=80, scheme='http'):
    ub = url_builder(host, port, scheme)

    r = requests.get(ub.url('doc'))
    r.raise_for_status()
    return r.json()


def do_get(url):
    return unpack_rest_response(requests.get(url))


def do_post(url, data={}):
    headers = {'Content-Type': 'application/json'}
    return unpack_rest_response(requests.post(url, data=json.dumps(data),
                                              headers=headers))
