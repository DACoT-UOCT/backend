import unittest
from deploy.api_seed import APISeed

class TestAPISeed(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestAPISeed, self).__init__(*args, **kwargs)

    def test_runtime_seed(self):
        seed = APISeed(
            'http://127.0.0.1:8081/graphql',
            'tests/cmodels.csv',
            'tests/juncs.csv',
            'tests/scheds.json',
            'tests/communes_reg_metrop.json'
        )
        seed.set_api_credentials('xs4MD75', '0SQ_t[cu+6')
        seed.runtime_seed()

    def test_runtime_seed_missing_credentials(self):
        seed = APISeed(
            'http://127.0.0.1:8081/graphql',
            'tests/cmodels.csv',
            'tests/juncs.csv',
            'tests/scheds.json',
            'tests/communes_reg_metrop.json'
        )
        try:
            seed.runtime_seed()
        except RuntimeError as err:
            assert 'call set_api_credentials first' in str(err)
