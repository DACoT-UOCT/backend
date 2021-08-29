import pytest

user = 'create_user@server.com'

def get_users(api):
	res = api.execute('query { users { email disabled } }')
	return [u['email'] for u in res['data']['users'] if not u['disabled']]

def test_user_mutations_create_user(dacot):
	qry = '''
		mutation {
			createUser(data: {
		    	fullName: "Demo User",
		    	email: "EMAIL",
		    	role: "Personal UOCT",
				area: "TIC",
		    	isAdmin: false
		  	}) {
		    	email
		  	}
		}
	'''.replace('EMAIL', user)
	dacot.execute(qry)
	users = get_users(dacot)
	assert len(users) > 0
	assert user in users

def test_user_mutations_delete_user(dacot):
	qry = '''
	mutation {
		deleteUser(data: {
			email: "EMAIL"
		})
	}
	'''.replace('EMAIL', user)
	dacot.execute(qry)
	users = get_users(dacot)
	assert len(users) == 0
	assert user not in users

def test_user_mutations_enable_user(dacot):
	qry = '''
	mutation {
		enableUser(data: {
			email: "EMAIL"
		})
	}
	'''.replace('EMAIL', user)
	dacot.execute(qry)
	users = get_users(dacot)
	assert len(users) > 0
	assert user in users
