# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

# Copyright (C) 2014  Sangoma Technologies Corp.
# All Rights Reserved.
# Author(s)
# Simon Gomizelj <sgomizelj@sangoma.com>

import re
import json
import keyword
import requests
import logging
from .url import url_builder, unpack_rest_response
from .library import CommitIncomplete, parse_messages
from .parser import parse
from .utils import deprecated


__all__ = ['api']

logger = logging.getLogger('safepy2')


def make_typename(name):
    '''Sanitize a name to remove spaces and replace all instances of
    symbols which are not valid for python types with underscore. Should
    the name be None, return RestObject for compatibility. Eventually
    a strict more will raise an exception instead'''

    if name is None:
        return str('RestObject')

    name = name.replace(' ', '')
    name = re.sub('[^a-zA-Z0-9_]', '_', name)

    if not all(c.isalnum() or c == '_' for c in name):
        raise ValueError('Type names and field names can only contain '
                         'alphanumeric characters and underscores: '
                         '{!r}'.format(name))
    if name[0].isdigit():
        raise ValueError('Type names and field names cannot start with '
                         'a number: {!r}'.format(name))
    if keyword.iskeyword(name):
        raise ValueError('Type names and field names cannot be a '
                         'keyword: {!r}'.format(name))

    return str(name)


def make_docstring(description):
    '''Make a valid docstring. Needs to be handled carefully since
    sometimes the json specification returns an array instead of a list.'''

    if description is None:
        return None

    if isinstance(description, list):
        description = '\n'.join(description)

    return str(description)


class APIWrapper(object):
    def __init__(self, node, version, session, builder):
        self.node = node
        self.version = version
        self.session = session
        self.builder = builder

    @property
    def interface(self):
        if self.node:
            return [node.tag for node in self.node.cls]

    @property
    def methods(self):
        if self.node:
            return [node.tag for node in self.node.methods]

    def __contains__(self, key):
        return key in self.interface

    def get_child(self, key):
        new_builder = self.builder.join(key)
        new_api = APIWrapper(self.node, self.version,
                             self.session, new_builder)
        return build_type(self.node, new_api, APIObject)(key)

    def get_config(self):
        safe_url = self.builder.url(None, section='config')
        return unpack_rest_response(self.session.get(safe_url))

    def upload(self, filename, payload=None):
        if not payload:
            with open(filename) as fp:
                payload = fp.read()

        files = {'archive': (filename, payload)}
        safe_url = self.builder.url('upload')
        return unpack_rest_response(self.session.post(safe_url, files=files))

    def get(self, method, path=None, params=None):
        safe_url = self.builder.url(method, path=path)
        return unpack_rest_response(self.session.get(safe_url, params=params))

    def post(self, method, path=None, data=None, params=None):
        postdata = json.dumps(data) if data else None
        safe_url = self.builder.url(method, path=path)
        data = self.session.post(safe_url, data=postdata,
                                 params=params,
                                 headers={'Content-Type': 'application/json'})
        return unpack_rest_response(data)


def api_wrapper(session, builder):
    version_url = builder.url('retrieve', path=['nsc', 'version'])
    version_data = unpack_rest_response(session.get(version_url)).data
    version = (int(version_data['major_version']),
               int(version_data['minor_version']),
               int(version_data['patch_version']))

    return APIWrapper(None, version, session, builder)


class API(object):
    def config(self):
        return self.api.get_config().content

    def changelog(self):
        return parse_messages(self.nsc.configuration.status())

    def commit(self):
        if 'smartapply' in self.nsc.configuration.api.methods:
            logger.info('Applying configuration')
            self.nsc.configuration.smartapply()
            state = self.nsc.configuration.status()
        else:
            logger.info('Attempting to apply configuration...')
            state = self.nsc.configuration.status()

            # Attempt to just reload the NSC configuration
            if state['modified'] and state['can_reload']:
                logger.info('Trying reload...')
                self.nsc.configuration.reload()
                state = self.nsc.configuration.status()

            # Changes may still now require us to restart the nsc service
            # to apply
            if state['modified']:
                status = self.nsc.service.status()['status_text']
                if status == 'RUNNING':
                    logger.info('Suspending NSC')
                    self.nsc.service.stop()
                logger.info('Trying apply...')
                self.nsc.configuration.apply()
                if status == 'RUNNING':
                    self.nsc.service.start()
                state = self.nsc.configuration.status()

        if state['modified']:
            raise CommitIncomplete(parse_messages(state))


class APICollection(object):
    def create(self, key, data):
        if 'display-name' in self.api.interface and 'display-name' not in data:
            data['display-name'] = key

        self.api.post('create', path=[key], data=data)
        return self[key]

    def delete(self, key):
        self.api.post('delete', path=[key])

    def update(self, key, data):
        self.api.post('update', path=[key], data=data)

    def retrieve(self, key):
        return self.api.get('retrieve', path=[key]).data

    def keys(self):
        return self.api.get('list').data

    def find(self, filter_expr):
        if not filter_expr:
            keys = self.api.get('list').data
        elif self.api.version >= (2, 1, 13):
            expression = {'filter': filter_expr}
            keys = self.api.post('list', data=expression).data
        else:
            raise NotImplementedError("No REST support for searching on 2.1")

        return iter(self[key] for key in keys)

    search = deprecated('Method renamed to find')(find)

    def __getitem__(self, key):
        return self.api.get_child(key)

    def __contains__(self, key):
        return key in self.keys()

    def __iter__(self):
        return iter(self[key] for key in self.keys())

    def __len__(self):
        return len(self.keys())

    def __bool__(self):
        return bool(self.keys())

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self.keys())


class APIObject(object):
    def __init__(self, name=None):
        if name:
            self.ident = name

    def __contains__(self, key):
        return key in self.api.interface

    def __repr__(self):
        try:
            return '{}({!r})'.format(self.__class__.__name__, self.retrieve())
        except AttributeError:
            return '{}()'.format(self.__class__.__name__)


def add_methods(ast, reserved=None):
    '''Compile all the methods specified in the json 'methods' section.
    Prefer specialized implementations of common and important rest
    functions, falling back to a generic implementation for others.'''
    def method_builder(func):
        def inner(node):
            method = func(node.tag)
            method.__name__ = make_typename(node.tag)
            method.__doc__ = make_docstring(node.get('description', None))
            return node.tag, method

        return inner

    @method_builder
    def make_upload_method(nodeid):
        def upload(self, filename, payload=None):
            return self.api.upload(filename, payload=payload).data
        return upload

    @method_builder
    def make_download_method(nodeid):
        def download(self, *args):
            return self.api.get(nodeid, path=args).content
        return download

    @method_builder
    def make_retrieve_method(nodeid):
        def retrieve(self):
            return self.api.get('retrieve').data
        return retrieve

    @method_builder
    def make_update_method(nodeid):
        def update(self, data):
            return self.api.post('update', data=data).data
        return update

    def make_getitem_method(nodeit):
        def __getitem__(self, key):
            return self.retrieve()[key]
        return '__getitem__', __getitem__

    def make_setitem_method(nodeid):
        def __setitem__(self, key, value):
            self.update({key: value})
        return '__setitem__', __setitem__

    @method_builder
    def make_get_method(nodeid):
        def get(self, *args, **kwargs):
            r = self.api.get(nodeid, path=args, params=kwargs)
            assert r.mimetype == 'application/json'
            return r.data
        return get

    @method_builder
    def make_post_method(nodeid):
        def post(self, *args, **kwargs):
            if args and isinstance(args[-1], dict):
                r = self.api.post(nodeid, path=args[:-1], data=args[-1],
                                  params=kwargs)
            else:
                r = self.api.post(nodeid, path=args)
            assert r.mimetype == 'application/json'
            return r.data
        return post

    for node in ast:
        if node.tag == 'list' or (reserved and node.tag in reserved):
            continue
        elif node.tag == 'retrieve':
            yield make_retrieve_method(node)
            yield make_getitem_method(node)
        elif node.tag == 'update':
            yield make_update_method(node)
            yield make_setitem_method(node)
        elif node.tag == 'upload':
            yield make_upload_method(node)
        elif node.tag == 'download':
            yield make_download_method(node)
        elif node['request'] == 'GET':
            yield make_get_method(node)
        elif node['request'] == 'POST':
            yield make_post_method(node)


def build_type(node, api, base):
    typename = make_typename(node.get('name', None))
    docstring = make_docstring(node.get('description'))

    namespace = {'__doc__': docstring, 'api': api}
    namespace.update(add_children(node.objs, api))
    namespace.update(add_methods(node.methods, base.__dict__))
    return type(typename, (base,), namespace)


def add_children(ast, api):
    for node in ast:
        new_builder = api.builder.join(node.tag)
        new_api = APIWrapper(node, api.version, api.session, new_builder)

        typename = make_typename(node.tag)
        base = APICollection if node.collection else APIObject
        yield typename, build_type(node, new_api, base)()


def api(host, port=80, scheme='http', token=None, specfile=None, timeout=None):
    '''Connects to a remote device, download the json specification
    describing the supported rest calls and dynamically compile a new
    object to wrap the rest.

    :param name: The hostname of the device to connect to.
    :type name: str
    :param port: The port the SAFe framework is listening on.
    :type port: int
    :param scheme: Specify the scheme of the request url.
    :type scheme: str
    :returns: the dynamically generated code.
    '''
    builder = url_builder(host, port, scheme)
    session = requests.session()
    if timeout:
        session.timeout = timeout
    if token:
        session.headers['X-API-KEY'] = token

    api = api_wrapper(session, builder)
    if not specfile:
        logger.info('Retrieving specification from NSC')
        r = session.get(builder.url(None, section='doc'))
        spec = unpack_rest_response(r).content
    else:
        with open(specfile) as fp:
            spec = json.load(fp)

    namespace = dict(add_children(parse(spec), api))
    product_cls = type('API', (API,), namespace)
    return product_cls()
