import pytest
from graphql.language.ast import IntValue
import fastapi_backend.app.graphql_models as models

def test_range_scalar_coerce_int():
	m = models.RangeScalar()
	r = m.coerce_int(10)
	assert r == 10

def test_range_scalar_coerce_int_limit():
	m = models.RangeScalar()
	try:
		m.coerce_int(models.RANGE_SCALAR_MAX_VALUE + 1)
	except ValueError:
		return

def test_range_scalar_parse_literal():
	m = models.RangeScalar()
	r = m.parse_literal(IntValue(value='10'))
	assert r == 10

def test_range_scalar_parse_literal_limit():
	m = models.RangeScalar()
	try:
		m.parse_literal(IntValue(value=str(models.RANGE_SCALAR_MAX_VALUE + 1)))
	except ValueError:
		return
