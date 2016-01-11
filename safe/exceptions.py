# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

# Copyright (C) 2015  Sangoma Technologies Corp.
# All Rights Reserved.
# Author(s)
# Simon Gomizelj <sgomizelj@sangoma.com>

import six
import requests


def flatten_error(error, parent=''):
    for path, value in six.iteritems(error):
        fullpath = '/'.join((parent, path)) if parent else path
        if isinstance(value, dict):
            for message in flatten_error(value, fullpath):
                yield message
        else:
            yield ': '.join((fullpath, value or 'unknown error'))


def flatten_reason(reasons):
    for reason in reasons:
        yield reason['description']


class APIError(requests.HTTPError):
    pass


class Reason(object):
    def __init__(self, reason):
        self.name = reason.get('obj_name')
        self.obj = reason['obj_type']
        self.description = reason['description']
        self.module = reason['module']

    def __str__(self):
        return self.description


class CommitFailed(APIError):
    def __init__(self, reasons, response=None):
        super(CommitFailed, self).__init__('Commit failed', response=response)
        self.reasons = reasons

    @classmethod
    def fromjson(cls, json, response=None):
        return cls([Reason(reason) for reason in json], response=response)

    def __str__(self):
        reasons = (str(reason) for reason in self.reasons)
        return u'Apply changes failed: {}'.format('\n'.join(reasons))


def raise_from_json(r):
    """Return stored :class:`APIError`, if one occurred."""
    data = r.json()
    api_error_message = None

    # Beware the bizarre formatting of error messages! The error field
    # can be, infuriatingly, one of a few possible types:
    #
    #   - an actual, raw, unwrapped error message
    #   - an error key with a raw message (like in the case of Conflict)
    #   - an error key with a list of strings that need to be joined
    #     into a full message
    #   - an error key holding a dictionary with a 'message' key
    #   - an error key holding a nested set of dictionaries representing
    #     paths and corresponding messages
    #   - potentially yet even more, bizarre, inconsistent styles
    if isinstance(data, six.string_types):
        return APIError(data, response=r)

    error = data.get('error')
    if isinstance(error, list):
        message = '\n'.join(error)
    elif isinstance(error, dict):
        reasons = error.get('reason')
        message = error.get('message')
        if reasons:
            return CommitFailed.fromjson(reasons, response=r)
        elif not message:
            message = error.get('msg')
            if not message:
                message = '\n'.join(flatten_error(error))
            else:
                obj = error['obj'][0]
                message = "In use by {} '{}'".format(obj['obj_type'],
                                                     obj['obj_name'])
    else:
        message = str(error)

    name = data.get('name')
    if message == 'Conflict':
        api_error_message = "The key '{}' is in conflicts with the "\
                            "system".format(name)
    elif name:
        api_error_message = 'Error for {}: {}'.format(name, message)
    else:
        api_error_message = message

    return APIError(api_error_message, response=r)
