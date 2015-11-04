# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

# Copyright (C) 2014  Sangoma Technologies Corp.
# All Rights Reserved.
# Author(s)
# Simon Gomizelj <sgomizelj@sangoma.com>

'''Convert the SAFe specification string into an abstract syntax tree
represeting its structure.
'''


import six
from .url import url_builder


class Node(dict):
    def __init__(self, tag, path, spec, objs=None, cls=None, methods=None):
        self.tag = tag
        self.path = path
        self.objs = objs
        self.cls = cls
        self.methods = methods

        self.update(spec)

    def __repr__(self):
        return '{}(tag={}, cls={}, methods={}, objs={}, {})'.format(
            self.__class__.__name__, self.tag,
            self.cls, self.methods, self.objs,
            dict.__repr__(self)
        )


class ObjectNode(Node):
    @property
    def singleton(self):
        # Because modules are objects except for when they're not.
        # Modules are objects that are always singletons but, unlike
        # other objects, don't report it.
        if len(self.path) == 1:
            return True
        return self.get('singleton', False)

    @property
    def isobject(self):
        method_names = set(node.tag for node in self.methods)
        return method_names.issuperset(('update', 'retrieve'))


class MethodNode(Node):
    pass


class ClassNode(Node):
    pass


def _parse_object(tag, spec, path=(), cls=ObjectNode):
    new_path = path + (tag,)

    def parse_node(section, cls):
        subspec = spec.pop(section, None)
        if not subspec or not isinstance(subspec, dict):
            return []
        return [_parse_object(*d, path=new_path, cls=cls)
                for d in six.iteritems(subspec)]

    return cls(tag, new_path, spec,
               objs=parse_node('object', ObjectNode),
               cls=parse_node('class', ClassNode),
               methods=parse_node('methods', MethodNode))


def parse(spec):
    return [_parse_object(*d) for d in six.iteritems(spec)]


def parse_from_url(host, port=80, scheme='http', token=None):
    '''Parse the SAFe documentation specification.

    :param name: The hostname of the device to connect to.
    :type name: str
    :param port: The port the SAFe framework is listening on.
    :type port: int
    :param scheme: Specify the scheme of the request url.
    :type scheme: str
    :returns: The abstract syntax tree represeting the specification.
    '''
    ub = url_builder(host, port, scheme, token=token)
    return parse(ub.get('doc').content)
