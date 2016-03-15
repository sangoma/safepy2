# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

# Copyright (C) 2014  Sangoma Technologies Corp.
# All Rights Reserved.
# Author(s)
# Simon Gomizelj <sgomizelj@sangoma.com>

'''Convert the SAFe specification string into an abstract syntax tree
represeting its structure.
'''


import six
from .url import get_documentation


class Node(dict):
    def __init__(self, tag, path, spec, objs=None, cls=None, methods=None):
        super(Node, self).__init__()
        self.tag = tag
        self.path = path
        self.objs = objs
        self.cls = cls
        self.methods = methods
        self.update(spec)

    @property
    def collection(self):
        return len(self.path) > 1 and not self.get('singleton', False)

    def __repr__(self):
        return '{}(tag={}, cls={}, methods={}, objs={}, {})'.format(
            self.__class__.__name__, self.tag,
            self.cls, self.methods, self.objs,
            dict.__repr__(self)
        )


class ObjectNode(Node):
    pass


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


def parse_from_url(*args, **kwargs):
    '''Parse the SAFe documentation specification.

    :param name: The hostname of the device to connect to.
    :type name: str
    :param port: The port the SAFe framework is listening on.
    :type port: int
    :param scheme: Specify the scheme of the request url.
    :type scheme: str
    :returns: The abstract syntax tree represeting the specification.
    '''
    return parse(get_documentation(*args, **kwargs))
