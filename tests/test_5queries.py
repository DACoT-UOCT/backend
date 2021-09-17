import pytest

def test_query_users(dacot):
	qry = '{ users(showDisabled:false) { id } }'
	res = dacot.execute(qry)
	assert 'errors' not in res
	assert res['data'] != None

def test_query_users_show_disabled(dacot):
	qry = '{ users(showDisabled:true) { id } }'
	res = dacot.execute(qry)
	assert 'errors' not in res
	assert res['data'] != None
