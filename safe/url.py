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


class APIError(requests.HTTPError):
    pass


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


def raise_api_error(r):
    """Raises stored :class:`APIError`, if one occurred."""

    data = r.json()
    api_error_message = None

    if isinstance(data, basestring):
        raise APIError(data, response=r)

    error = data.get('error', None)
    if error == 'Conflict':
        api_error_message = "The key '{}' is in conficts with the "\
                            "system".format(data['name'])
        raise APIError(api_error_message, response=r)

    # The error field can be, infuriatingly, one of a few possible
    # types: a straight error message (liw above with Conflict),
    # a dictionary ({'message': ...}), or a list of seperate lines.
    try:
        message = error.get('message')
    except AttributeError:
        message = error

    if isinstance(message, list):
        message = '\n'.join(message)

    if message:
        api_error_message = 'Error on {}: {}'.format(data['name'], message)
        raise APIError(api_error_message, response=r)


def raise_for_status(r):
    """Raises stored :class:`requests.HTTPError`, if one occurred."""

    http_error_msg = None
    if 400 <= r.status_code < 500:
        if r.headers['content-type'] == 'application/json':
            raise_api_error(r)
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
    '''
    .. note::
       This class isn't intended to be constructed directly, use
       :func:`sangoma.safepy.url.url_builder` instead.

    Builder for SAFe REST api urls. A functional structure which stores
    a path and allows itself to be cloned to append more information.
    '''

    def __init__(self, base, session, segments=None):
        self.base = base
        self.session = session
        self.segments = segments or ()


    def __call__(self, *segments):
        '''Create a new copy of the url builder with more segments
        appended to the new object builder.

        :param args: Any positional arguments for appending.
        '''

        segments = self.segments + segments
        return UrlBuilder(self.base, self.session, segments)

    def url(self, prefix, method=None, keys=()):
        '''Render a specific url to string.

        :param prefix: The prefix, for example, 'doc' or 'api'.
        :type prefix: str
        :param method: The optional method, if generating a method call.
        :type method: str
        '''
        prefix = (prefix, method) if method else (prefix,)
        segments = prefix + self.segments + tuple(keys)
        return urlparse.urljoin(self.base, '/'.join(segments))

    def upload(self, prefix, filename, payload=None):
        if not payload:
            with open(filename) as archive:
                payload = archive.read()

        data = self.session.post(self.url(prefix, method='upload'),
                                 files={'archive': (filename, payload)})
        return unpack_rest_response(data)

    def get(self, prefix, method=None, keys=()):
        data = self.session.get(self.url(prefix, method=method, keys=keys))
        return unpack_rest_response(data)

    def post(self, prefix, method=None, keys=(), data=None):
        postdata = json.dumps(data) if data else None
        safe_url = self.url(prefix, method=method, keys=keys)
        data = self.session.post(safe_url, data=postdata,
                                 headers={'Content-Type': 'application/json'})
        return unpack_rest_response(data)


def url_builder(host, port=80, scheme='http', token=None):
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

    session = requests.Session()
    if token:
        session.headers['X-API-KEY'] = token

    return UrlBuilder(base, session)


def dump_docs(filepath, host, port=80, scheme='http', token=None):
    ub = url_builder(host, port, scheme, token=token)
    with open(filepath, 'w') as fp:
        json_spec = ub.get('doc').content
        json.dump(json_spec, fp,
                  sort_keys=True,
                  indent=4,
                  separators=(',', ': '))
