#vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

# Copyright (C) 2014  Sangoma Technologies Corp.
# All Rights Reserved.
# Author(s)
# Simon Gomizelj <sgomizelj@sangoma.com>

import re
import json
import keyword
from .url import url_builder
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


class API(object):
    def commit(self):
        state = self.nsc.configuration.status()

        # Attempt to just reload the NSC configuration
        if state['modified'] and state['can_reload']:
            self.nsc.configuration.reload()
            state = self.nsc.configuration.status()

        # Changes may still now require us to restart the nsc service
        # to apply
        if state['modified']:
            self.nsc.configuration.apply()
            state = self.nsc.configuration.status()

        if state['modified']:
            raise RuntimeError('Failed to apply pending changes')


class APICollection(object):
    def __init__(self, node, ub):
        self.node = node
        self.interface = [t.tag for t in node.cls]
        self._ub = ub

    def _list(self, filter_expr=None):
        if not filter_expr:
            return self._ub.get('api', 'list').data

        return self._ub.post('api', 'list',
                             data={'filter': filter_expr}).data

    def create(self, key, data={}):
        self._ub(key).post('api', 'create', data=data)
        return self[key]

    def delete(self, key):
        self._ub(key).post('api', 'delete')

    def update(self, key, data):
        self._ub(key).post('api', 'update', data=data)

    def retrieve(self, key):
        return self._ub(key).get('api', 'retrieve').data

    def keys(self):
        return self._list()

    def search(self, filter_expr):
        return iter(self[item] for item in self._list(filter_expr))

    def __getitem__(self, key):
        return compile_child(self.node, self._ub(key))

    def __contains__(self, key):
        return key in self._list()

    def __iter__(self):
        return iter(self[item] for item in self._list())

    def __len__(self):
        return len(self._list())

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self._list())


class APIObject(object):
    def __init__(self, node, ub):
        self._interface = [t.tag for t in node.cls]
        self._ub = ub

    def retrieve(self):
        return self._ub.get('api', 'retrieve').data

    def update(self, data):
        self._ub.post('api', 'update', data=data).data

    def __contains__(self, key):
        return key in self._interface

    def __getitem__(self, key):
        return self.retrieve()[key]

    def __setitem__(self, key, value):
        self.update({key: value})

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self.retrieve())


class APIModule(object):
    def __init__(self, node, ub):
        self._interface = [t.tag for t in node.cls]
        self._ub = ub

    def __contains__(self, key):
        return key in self._interface

    def __getitem__(self, key):
        return self.retrieve()[key]

    def __repr__(self):
        return '{}()'.format(self.__class__.__name__)


def compile_methods(ast, ub, cls):
    '''Compile all the methods specified in the json 'methods' section.
    Prefer specialized implementations of common and important rest
    functions, falling back to a generic implementation for others.'''

    def make_upload_method(ub, nodeid):
        def upload(self, filename, payload=None):
            return ub.upload('api', filename, payload=None).data
        return upload

    def make_download_method(ub, nodeid, *arg):
        def download(self, *args):
            return ub.get('api', nodeid, keys=args).content
        return download

    def make_get_method(ub, nodeid, *arg):
        def get(self, *args):
            r = ub.get('api', nodeid, keys=args)
            assert r.mimetype == 'application/json'
            return r.data
        return get

    def make_post_method(ub, nodeid):
        def post(self, *args):
            if args and isinstance(args[-1], dict):
                r = ub.post('api', nodeid,
                            keys=args[:-1],
                            data=args[-1])
            else:
                r = ub.post('api', nodeid, keys=args)

            assert r.mimetype == 'application/json'
            return r.data
        return post

    namespace = {'ident': ub.segments[-1]}
    for node in ast:
        if node.tag in cls.__dict__:
            continue

        if node.tag == 'upload':
            method = make_upload_method(ub, node.tag)
        elif node.tag == 'download':
            method = make_download_method(ub, node.tag)
        elif node['request'] == 'GET':
            method = make_get_method(ub, node.tag)
        elif node['request'] == 'POST':
            method = make_post_method(ub, node.tag)

        method.__name__ = make_typename(node.tag)
        method.__doc__ = make_docstring(node.get('description', None))
        namespace[method.__name__] = method

    return namespace


def object_template(node):
    typename = make_typename(node.get('name', None))
    docstring = make_docstring(node.get('description', None))

    return typename, {'__doc__': docstring}


def compile_child(node, ub):
    typename, namespace = object_template(node)
    cls = APIObject if node.isobject else APIModule

    namespace.update(compile_objects(node.objs, ub))
    namespace.update(compile_methods(node.methods, ub, cls))

    return type(typename, (cls,), namespace)(node, ub)


def compile_collection(node, ub):
    typename, namespace = object_template(node)

    namespace.update(compile_methods(node.methods, ub, APICollection))
    return type(typename, (APICollection,), namespace)(node, ub)


def compile_object(node, ub):
    '''Compile an object from the json specification. An object can be
    composed of methods and other objects. In the case that the object
    is not marked as a 'singleton', treat is like a collection and tack
    on a __getitem__ handler.'''

    if node.singleton:
        return compile_child(node, ub(node.tag))
    else:
        return compile_collection(node, ub(node.tag))


def compile_objects(ast, ub):
    return {make_typename(n.tag): compile_object(n, ub) for n in ast}


def api(host, port=80, scheme='http', token=None, specfile=None):
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

    ub = url_builder(host, port, scheme, token=token)
    if not specfile:
        spec = ub.get('doc').content
    else:
        with open(specfile) as fp:
            spec = json.load(fp)

    ast = parse(spec)
    namespace = compile_objects(ast, ub)
    product_cls = type('API', (API,), namespace)
    return product_cls()
