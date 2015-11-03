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
