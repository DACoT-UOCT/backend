import pytest

@pytest.mark.parametrize('v', ['data', 'value'])
def test_print_parameter(v):
    print(v)

