#vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

# Copyright (C) 2014  Sangoma Technologies Corp.
# All Rights Reserved.
# Author(s)
# Simon Gomizelj <sgomizelj@sangoma.com>

import re
import json
import keyword
import requests
from .url import url_builder, unpack_rest_response
from .parser import parse


__all__ = ['api']


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

    def __contains__(self, key):
        return key in self.interface

    def get_child(self, key):
        new_builder = self.builder.join(key)
        new_api = APIWrapper(self.node, self.version, self.session, new_builder)
        return compile_child(self.node, new_api)

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

    def get(self, method, path=None):
        safe_url = self.builder.url(method, path=path)
        return unpack_rest_response(self.session.get(safe_url))

    def post(self, method, path=None, data=None):
        postdata = json.dumps(data) if data else None
        safe_url = self.builder.url(method, path=path)
        data = self.session.post(safe_url, data=postdata,
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
    def __init__(self, api):
        self.api = api

    def config(self):
        return self.api.get_config().content

    def commit(self):
        state = self.nsc.configuration.status()

        # Attempt to just reload the NSC configuration
        if state['modified'] and state['can_reload']:
            self.nsc.configuration.reload()
            state = self.nsc.configuration.status()

        # Changes may still now require us to restart the nsc service
        # to apply
        if state['modified']:
            status = self.nsc.service.status()['status_text']
            if status == 'RUNNING':
                self.nsc.service.stop()
            self.nsc.configuration.apply()
            if status == 'RUNNING':
                self.nsc.service.start()
            state = self.nsc.configuration.status()

        if state['modified']:
            raise RuntimeError('Failed to apply pending changes')


class APICollection(object):
    def __init__(self, api):
        self.api = api

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

    def search(self, filter_expr):
        if not filter_expr:
            keys = self.api.get('list').data
        elif self.api.version >= (2, 1, 13):
            expression = {'filter': filter_expr}
            keys = self.api.post('list', data=expression).data
        else:
            raise NotImplementedError("No REST support for searching on 2.1")

        return iter(self[key] for key in keys)

    def __getitem__(self, key):
        return self.api.get_child(key)

    def __contains__(self, key):
        return key in self.keys()

    def __iter__(self):
        return iter(self[key] for key in self.keys())

    def __len__(self):
        return len(self.keys())

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self.keys())


class APIObject(object):
    def __init__(self, api):
        self.api = api

    def retrieve(self):
        return self.api.get('retrieve').data

    def update(self, data):
        return self.api.post('update', data=data).data

    def __getitem__(self, key):
        return self.retrieve()[key]

    def __setitem__(self, key, value):
        self.update({key: value})

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self.retrieve())


class APIModule(object):
    def __init__(self, api):
        self.api = api

    def __getitem__(self, key):
        return self.retrieve()[key]

    def __repr__(self):
        try:
            data = self.retrieve()
            return '{}({!r})'.format(self.__class__.__name__, data)
        except AttributeError:
            return '{}()'.format(self.__class__.__name__)


def compile_methods(ast, api, reserved=None):
    '''Compile all the methods specified in the json 'methods' section.
    Prefer specialized implementations of common and important rest
    functions, falling back to a generic implementation for others.'''

    def make_upload_method(api, nodeid):
        def upload(self, filename, payload=None):
            return api.upload(filename, payload=payload).data
        return upload

    def make_download_method(api, nodeid, *arg):
        def download(self, *args):
            return api.get(nodeid, *args).content
        return download

    def make_get_method(api, nodeid, *arg):
        def get(self, *args):
            r = api.get(nodeid, *args)
            assert r.mimetype == 'application/json'
            return r.data
        return get

    def make_post_method(api, nodeid):
        def post(self, *args):
            if args and isinstance(args[-1], dict):
                r = api.post(nodeid, path=args[:-1], data=args[-1])
            else:
                r = api.post(nodeid, data=args)

            assert r.mimetype == 'application/json'
            return r.data
        return post

    for node in ast:
        if node.tag == 'list':
            continue
        if reserved and node.tag in reserved:
            continue

        if node.tag == 'upload':
            method = make_upload_method(api, node.tag)
        elif node.tag == 'download':
            method = make_download_method(api, node.tag)
        elif node['request'] == 'GET':
            method = make_get_method(api, node.tag)
        elif node['request'] == 'POST':
            method = make_post_method(api, node.tag)

        method.__name__ = make_typename(node.tag)
        method.__doc__ = make_docstring(node.get('description', None))
        yield method.__name__, method


def object_template(node):
    typename = make_typename(node.get('name', None))
    return typename, {'ident': node.tag,
                      '__doc__': make_docstring(node.get('description', None))}


def compile_child(node, api):
    typename, namespace = object_template(node)
    namespace.update(compile_objects(node.objs, api))
    namespace.update(compile_methods(node.methods, api, APIObject.__dict__))
    return type(typename, (APIObject,), namespace)(api)


def compile_module(node, api):
    typename, namespace = object_template(node)
    namespace.update(compile_objects(node.objs, api))
    namespace.update(compile_methods(node.methods, api))
    return type(typename, (APIModule,), namespace)(api)


def compile_collection(node, api):
    typename, namespace = object_template(node)
    namespace.update(compile_methods(node.methods, api, APICollection.__dict__))
    return type(typename, (APICollection,), namespace)(api)


def compile_objects(ast, api):
    for node in ast:
        typename = make_typename(node.tag)
        new_builder = api.builder.join(node.tag)
        new_api = APIWrapper(node, api.version, api.session, new_builder)

        if node.singleton:
            yield typename, compile_module(node, new_api)
        else:
            yield typename, compile_collection(node, new_api)


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
        r = session.get(builder.url(None, section='doc'))
        spec = unpack_rest_response(r).content
    else:
        with open(specfile) as fp:
            spec = json.load(fp)

    namespace = dict(compile_objects(parse(spec), api))
    product_cls = type('API', (API,), namespace)
    return product_cls(api)
