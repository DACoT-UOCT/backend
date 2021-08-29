import pytest

def get_users(api):
	res = api.execute('query { users { email disabled } }')
	return [u['email'] for u in res['data']['users'] if not u['disabled']]

def test_user_mutations_create_user(dacot):
	qry = '''
		mutation {
			createUser(data: {
		    	fullName: "Demo User",
		    	email: "create_user@server.com",
		    	role: "Personal UOCT",
				area: "TIC",
		    	isAdmin: false
		  	}) {
		    	email
		  	}
		}
	'''
	dacot.execute(qry)
	users = get_users(dacot)
	assert len(users) > 0
	assert 'create_user@server.com' in users

def test_user_mutations_delete_user(dacot):
	qry = '''
	mutation {
		deleteUser(data: {
			email: "create_user@server.com"
		})
	}
	'''
	dacot.execute(qry)
	users = get_users(dacot)
	assert len(users) == 0
	assert 'create_user@server.com' not in users

def test_user_mutations_enable_user(dacot):
	qry = '''
	mutation {
		enableUser(data: {
			email: "create_user@server.com"
		})
	}
	'''
	dacot.execute(qry)
	users = get_users(dacot)
	assert len(users) > 0
	assert 'create_user@server.com' in users
