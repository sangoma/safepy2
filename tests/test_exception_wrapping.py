import safe


class MockResponse(object):
    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data


def test_raw_exception():
    error_message = 'Forbidden'

    response = MockResponse(error_message)
    exception = safe.library.raise_from_json(response)
    assert str(exception) == error_message


def test_unwrapped_exception():
    error_message = 'Invalid API key'

    response = MockResponse({'status': False, 'error': error_message})
    exception = safe.library.raise_from_json(response)
    assert str(exception) == error_message


def test_unwrapped_multiline_exception():
    error_message = ['Line 1',
                     'Line 2',
                     'Line 3']

    response = MockResponse({'status': False, 'error': error_message})
    exception = safe.library.raise_from_json(response)
    assert str(exception) == '\n'.join(error_message)


def test_basic_exception():
    error_message = 'Example error'
    response = MockResponse({
        'status': False,
        'method': 'synchronize',
        'module': 'cluster',
        'error': {'message': error_message}
    })

    exception = safe.library.raise_from_json(response)
    assert str(exception) == error_message


def test_basic_exception_with_name():
    error_message = 'Internal is running'
    response = MockResponse({
        'status': False,
        'type': 'profile',
        'method': 'delete',
        'module': 'sip',
        'error': {'message': error_message},
        'name': 'Internal',
    })

    exception = safe.library.raise_from_json(response)
    assert str(exception) == 'Error for Internal: ' + error_message


def test_configuration_conflict_exception():
    response = MockResponse({
        'status': False,
        'type': 'profile',
        'method': 'create',
        'module': 'sip',
        'error': {'message': 'Conflict'},
        'name': 'Internal',
    })

    exception = safe.library.raise_from_json(response)
    assert str(exception) == "The key 'Internal' conflicts with the system"


def test_configuration_in_use_exception():
    response = MockResponse({
        'status': False,
        'type': 'domain',
        'method': 'delete',
        'module': 'directory',
        'error': {
            'message': 'upreg_domain is use by',
            'obj': [{
                'name': 'sip',
                'obj_name': 'external_upreg',
                'obj_type': 'profile'
            }],
        },
        'name': 'upreg_domain'
    })

    exception = safe.library.raise_from_json(response)
    assert str(exception) == "Error for upreg_domain: "\
        "In use by profile 'external_upreg'"


def test_configuration_validation_exception():
    gatewaydev_error = 'The Default Gateway Interface field is required.'
    hostname_error = 'The Host Name field must contain a valid domain.'
    response = MockResponse({
        'status': False,
        'type': 'configuration',
        'method': 'update',
        'module': 'network',
        'error': {
            'global/gatewaydev': gatewaydev_error,
            'global/hostname': hostname_error
        }
    })

    exception = safe.library.raise_from_json(response)
    assert 'global/hostname: ' + hostname_error in str(exception)
    assert 'global/gatewaydev: ' + gatewaydev_error in str(exception)


def test_commit_failed_exception():
    error_message = 'Default ipv4 gateway is not on eth0 subnet'
    response = MockResponse({
        'status': False,
        'type': 'configuration',
        'method': 'smartapply',
        'module': 'nsc',
        'error': {
            'message': 'Apply configuration failed.',
            'reason': [{
                'url': '/SAFe/sng_network_config/modify/network',
                'obj_type': 'configuration',
                'type': 'ERROR',
                'description': error_message,
                'module': 'network'
            }]
        }
    })

    exception = safe.library.raise_from_json(response)
    assert isinstance(exception, safe.CommitFailed)
    assert str(exception) == 'Apply changes failed: ' + error_message
    assert len(exception.reasons) == 1

    reason = exception.reasons[0]
    assert reason.obj == 'configuration'
    assert reason.module == 'network'
    assert reason.description == error_message
