import pytest
import safe


MOCK_DESCRIPTION = 'This is an mock ast'


@pytest.fixture
def safe_mock_ast():
    return safe.parser.parse({
        "mock": {
            "description": [
                MOCK_DESCRIPTION
            ],
            "name": "Mock",
            "object": {
                "configuration": {
                    "base_path": "/NSC/local/software/mock/configuration",
                    "class": {
                        "interface": {
                            "default": "all",
                            "field": "interface",
                            "help": "Select an interface",
                            "label": "Network Interface",
                            "rules": "required|in_list[all,eth0]",
                            "type": "dropdown",
                            "value": {
                                "all": "All interfaces",
                                "eth0": "eth0 - 192.0.2.1"
                            }
                        }
                    },
                    "configurable": True,
                    "description": "Configuration",
                    "dynamic": False,
                    "global_methods": False,
                    "methods": {
                        "retrieve": {
                            "name": "Retrieve",
                            "request": "GET"
                        },
                        "update": {
                            "name": "Update",
                            "request": "POST"
                        }
                    },
                    "name": "Configuration",
                    "pagination": False,
                    "singleton": True
                }
            }
        }
    })


def test_parse(safe_mock_ast):
    assert len(safe_mock_ast) == 1
    mock_ast = safe_mock_ast[0]

    assert mock_ast.tag == 'mock'
    assert mock_ast.cls == []
    assert mock_ast.methods == []
    assert mock_ast['description'] == [MOCK_DESCRIPTION]

    assert len(mock_ast.objs) == 1
    mock_obj = mock_ast.objs[0]

    # TODO: Probably should reconsider this API then
    assert mock_obj.cls[0].tag == 'interface'
    for node in mock_obj.methods:
        assert node.tag in ('retrieve', 'update')
