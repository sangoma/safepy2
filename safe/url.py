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
import itertools
import requests
from six.moves.urllib.parse import urljoin
from .library import APIError, raise_from_json


class APIResponse(object):
    def __init__(self, response):
        self.mimetype = response.headers['content-type']

        if self.mimetype == 'application/json':
            self.content = response.json()
        elif self.mimetype == 'application/x-gzip':
            self.content = response.content
        else:
            raise APIError("Unsupported content type: "
                           "{!r}".format(self.mimetype))

    @property
    def data(self):
        if self.mimetype == 'application/json':
            return self.content.get('data')

    @property
    def status(self):
        if self.mimetype == 'application/json':
            return bool(self.content.get('status'))
        return bool(self.content)

    def __nonzero__(self):
        return self.status


def raise_for_status(r):
    """Raises stored :class:`requests.HTTPError`, if one occurred."""

    http_error_msg = None
    if 400 <= r.status_code < 500:
        if r.headers['content-type'] == 'application/json':
            raise raise_from_json(r)
        http_error_msg = '{} Client Error: {} for url: '\
                         '{}'.format(r.status_code, r.reason, r.url)
    elif 500 <= r.status_code < 600:
        http_error_msg = '{} Server Error: {} for url: '\
                         '{}'.format(r.status_code, r.reason, r.url)

    if http_error_msg:
        raise requests.HTTPError(http_error_msg, response=r)


def unpack_rest_response(r):
    '''Interpret the response from a rest call. If we got an error,
    raise it. If not return either data or status, depending on
    availability'''

    raise_for_status(r)
    return APIResponse(r)


class UrlBuilder(object):
    '''Builder for SAFe REST api urls. A functional structure which
    stores a path and allows itself to be cloned to append more
    information.
    '''

    def __init__(self, base, segments=None):
        self.base = base
        self.segments = segments or ()

    def join(self, *segments):
        '''Create a new copy of the url builder with more segments
        appended to the new object builder.

        :param args: Any positional arguments for appending.
        '''
        return UrlBuilder(self.base, self.segments + segments)

    def url(self, method, path=None, section='api'):
        '''Render a specific url to string.

        :param prefix: The prefix, for example, 'doc' or 'api'.
        :type prefix: str
        :param method: The optional method, if generating a method call.
        :type method: str
        '''
        prefix = (section, method) if method else (section,)
        segments = itertools.chain(prefix, self.segments, path or [])
        return urljoin(self.base, '/'.join(segments))


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

    base_url = '{scheme}://{host}:{port}/SAFe/sng_rest/'.format(host=host,
                                                                port=port,
                                                                scheme=scheme)
    return UrlBuilder(base_url)


def get_documentation(host, port=80, scheme='http', token=None, timeout=None):
    headers = {}
    if token:
        headers['X-API-KEY'] = token

    builder = url_builder(host, port, scheme)
    safeurl = builder.url(None, section='doc')
    r = requests.get(safeurl, headers=headers, timeout=timeout)
    return unpack_rest_response(r).content


def dump_docs(filepath, *args, **kwargs):
    with open(filepath, 'w') as fp:
        json.dump(get_documentation(*args, **kwargs),
                  fp, sort_keys=True, indent=4, separators=(',', ': '))
