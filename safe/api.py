#vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

# Copyright (C) 2014  Sangoma Technologies Corp.
# All Rights Reserved.
# Author(s)
# Simon Gomizelj <sgomizelj@sangoma.com>

import re
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
        return 'RestObject'

    name = name.encode('ascii', 'ignore')
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

    return name


def make_docstring(description):
    '''Make a valid docstring. Needs to be handled carefully since
    sometimes the json specification returns an array instead of a list.'''

    if description is None:
        return None

    if isinstance(description, list):
        return '\n'.join(description)

    return description


# {{{ Make Functions
def make_getter(attr):
    def getter(self):
        return self.retrieve()[attr]
    return getter


def make_setter(attr):
    def setter(self, value):
        self.update({attr: value})
    return setter


def make_get_method(ub, nodeid, *arg):
    def get(self, *args):
        return ub.get('api', nodeid, keys=args).get('data')
    return get


def make_post_method(ub, nodeid):
    def post(self, *args):
        if args and isinstance(args[-1], dict):
            return ub.post('api', nodeid,
                           keys=args[:-1],
                           data=args[-1]).get('data')
        return ub.post('api', nodeid, keys=args).get('data')
    return post
# }}}


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
        self._ub = ub

    def list(self, filter_expr=None):
        if not filter_expr:
            return self._ub.get('api', 'list').get('data')

        return self._ub.post('api', 'list',
                             data={'filter': filter_expr}).get('data')

    def create(self, key, data={}):
        self._ub(key).post('api', 'create', data=data)
        return self[key]

    def delete(self, key):
        self._ub(key).post('api', 'delete')

    def update(self, key, data):
        self._ub(key).post('api', 'update', data=data)

    def retrieve(self, key):
        return self._ub(key).get('api', 'retrieve').get('data')

    def __getitem__(self, key):
        return compile_child(self.node, self._ub(key))

    def __contains__(self, key):
        return key in self.list()

    def __iter__(self):
        return iter(self.list())

    def __len__(self):
        return len(self.list())

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self.list())


class APIObject(object):
    def __init__(self, ub):
        self._ub = ub

    def retrieve(self):
        return self._ub.get('api', 'retrieve').get('data')

    def update(self, data):
        self._ub.post('api', 'update', data=data).get('data')

    def __getitem__(self, key):
        return self.retrieve()[key]

    def __setitem__(self, key, value):
        self.update({key: value})

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self.retrieve())


class APIModule(object):
    def __init__(self, ub):
        self._ub = ub

    def __getitem__(self, key):
        return self.retrieve()[key]

    def __repr__(self):
        return '{}()'.format(self.__class__.__name__)


def compile_methods(ast, ub, cls):
    '''Compile all the methods specified in the json 'methods' section.
    Prefer specialized implementations of common and important rest
    functions, falling back to a generic implementation for others.'''

    namespace = {'ident': ub.segments[-1]}
    for node in ast:
        if node.tag in cls.__dict__:
            continue

        if node['request'] == 'GET':
            method = make_get_method(ub, node.tag)
        elif node['request'] == 'POST':
            method = make_post_method(ub, node.tag)

        method.__name__ = make_typename(node.tag)
        method.__doc__ = make_docstring(node.get('description', None))
        namespace[method.__name__] = method

    return namespace


def compile_properties(ast):
    '''Compile all the attributes specified in the json 'class' section.
    Implemented as properties on the resulting class'''

    namespace = {}
    for node in ast:
        propname, docstring = make_typename(node.tag), node.get('help', None)
        namespace[propname] = property(make_getter(node.tag),
                                       make_setter(node.tag),
                                       None, docstring)

    return namespace


def object_template(node):
    typename = make_typename(node.get('name', None))
    docstring = make_docstring(node.get('description', None))

    return typename, {'__doc__': docstring}


def compile_child(node, ub):
    typename, namespace = object_template(node)
    cls = APIObject if node.isobject else APIModule

    namespace.update(compile_properties(node.cls))
    namespace.update(compile_objects(node.objs, ub))
    namespace.update(compile_methods(node.methods, ub, cls))

    return type(typename, (cls,), namespace)(ub)


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


def api(host, port=80, scheme='http'):
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

    ub = url_builder(host, port, scheme)
    ast = parse(host, port, scheme)

    typename = make_typename(host.partition('.')[0].capitalize())
    namespace = compile_objects(ast, ub)

    product_cls = type(typename, (API,), namespace)
    return product_cls()
