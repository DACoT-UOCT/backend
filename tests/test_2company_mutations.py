import pytest

def get_companies(api):
	res = api.execute('query { companies { name disabled } }')
	return [c['name'] for c in res['data']['companies'] if not c['disabled']]

def test_company_mutations_create_company(dacot):
	qry = '''
	mutation {
		createCompany(data: {
			name: "DemoCompany"
		}) {
			name
		}
	}
	'''
	dacot.execute(qry)
	companies = get_companies(dacot)
	assert len(companies) > 0
	assert 'DemoCompany' in companies

def test_company_mutations_delete_company(dacot):
	qry = '''
	mutation {
		deleteCompany(data: {
			name: "DemoCompany"
		})
	}
	'''
	dacot.execute(qry)
	companies = get_companies(dacot)
	assert len(companies) == 0
	assert 'DemoCompany' not in companies

def test_company_mutations_enable_company(dacot):
	qry = '''
	mutation {
		enableCompany(data: {
			name: "DemoCompany"
		})
	}
	'''
	dacot.execute(qry)
	companies = get_companies(dacot)
	assert len(companies) > 0
	assert 'DemoCompany' in companies
