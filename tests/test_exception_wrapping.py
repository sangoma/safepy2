import safe


class MockResponse(object):
    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data


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
