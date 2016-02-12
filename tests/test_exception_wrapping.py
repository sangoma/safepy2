import safe


def test_simple_exception():
    class MockReponse(object):
        def json(self):
            return {'status': False,
                    'method': 'synchronize',
                    'module': 'cluster',
                    'error': {'message': 'Example error'}}

    exception = safe.library.raise_from_json(MockReponse())
    assert str(exception) == 'Example error'
