# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

# Copyright (C) 2014  Sangoma Technologies Corp.
# All Rights Reserved.
# Author(s)
# Simon Gomizelj <sgomizelj@sangoma.com>

'''Convert the SAFe specification string into an abstract syntax tree
represeting its structure.
'''


from .nodes import *


def _parse_object(tag, spec, path=(), cls=ObjectNode):
    new_path = path + (tag,)

    def parse_node(section, cls):
        subspec = spec.pop(section, None)
        if not subspec:
            return []
        return [_parse_object(*d, path=new_path, cls=cls)
                for d in subspec.iteritems()]

    return cls(tag, new_path, spec,
               objs=parse_node('object', ObjectNode),
               cls=parse_node('class', ClassNode),
               methods=parse_node('methods', MethodNode))


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


def parse(url_builder):
    return [_parse_object(*d) for d in url_builder.get('doc').iteritems()]
