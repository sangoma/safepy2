# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

# Copyright (C) 2015  Sangoma Technologies Corp.
# All Rights Reserved.
# Author(s)
# Simon Gomizelj <sgomizelj@sangoma.com>

import six
import requests


class APIError(requests.HTTPError):
    pass


class Reason(object):
    def __init__(self, reason):
        self.name = reason.get('obj_name')
        self.obj = reason['obj_type']
        self.description = reason['description']
        self.module = reason['module']
        self.url = reason.get('url')

    def __str__(self):
        return self.description


class CommitFailed(APIError):
    def __init__(self, reasons, response=None):
        super(CommitFailed, self).__init__('Commit failed', response=response)
        self.reasons = reasons

    def __str__(self):
        reasons = (str(reason) for reason in self.reasons)
        return u'Apply changes failed: {}'.format('\n'.join(reasons))


class CommitIncomplete(RuntimeError):
    def __init__(self, messages):
        self.messages = messages

    def __str__(self):
        messages = (str(message) for message in self.messages)
        return u'Failed to apply all changes: {}'.format('\n'.join(messages))


class Status(object):
    def __init__(self, module, status, description=None):
        self.status = status
        self.module = module
        self.description = description or module

    @classmethod
    def fromjson(cls, item):
        return cls(item['module'], item['status'], item['description'])

    def __str__(self):
        return ' '.join((self.status, self.description))

    def __repr__(self):
        return '<Status({})>'.format(self)


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
    message = None
    if isinstance(error, list):
        message = '\n'.join(error)
    elif isinstance(error, dict):
        reasons = error.get('reason')
        if reasons:
            explanation = [Reason(reason) for reason in reasons]
            return CommitFailed(explanation, response=r)

        status = error.get('status')
        if status:
            checklist = status.get('checklist')
            if checklist:
                explanation = [Reason(reason) for reason in checklist['items']]
                return CommitFailed(explanation, response=r)

        obj = error.get('obj')
        message = error.get('message')
        if not message:
            message = '\n'.join(flatten_error(error))
        elif obj:
            message = "In use by {} '{}'".format(obj[0]['obj_type'],
                                                 obj[0]['obj_name'])

    if not message:
        message = str(error)

    name = data.get('name')
    if message == 'Conflict':
        api_error_message = "The key '{}' conflicts with the "\
                            "system".format(name)
    elif name:
        api_error_message = 'Error for {}: {}'.format(name, message)
    else:
        api_error_message = message

    return APIError(api_error_message, response=r)


def parse_messages(status):
    messages = []

    # NSC 2.2 and newer splits the pending changes into three
    # different sections, depending on the type of the configuration
    # and the running state of NSC... because.
    for section in ('reload', 'restart', 'apply'):
        pending = status.get(section)
        if pending:
            messages.extend(Status.fromjson(item) for item in pending['items'])

    # NSC 2.1 compatability
    pending = status.get('reloadable')
    if pending:
        messages.extend(Status(k, v['configuration'])
                        for k, v in six.iteritems(pending))

    return messages
