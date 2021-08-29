import pytest

def get_controllers(api, show_disabled=False):
	res = api.execute('query { controllers(showDisabled: true) { id model disabled } }')
	if not show_disabled:
		return [(c['id'], c['model']) for c in res['data']['controllers'] if not c['disabled']]
	else:
		return [(c['id'], c['model']) for c in res['data']['controllers']]

def test_controller_mutations_create_controller(dacot):
	qry = '''
		mutation {
			createController(data: {
				company: "DemoCompany",
				model: "DemoModel"
			}) {
				model
			}
		}
	'''
	dacot.execute(qry)
	controllers = get_controllers(dacot)
	assert len(controllers) > 0
	assert 'DemoModel' in [c[1] for c in controllers]

def test_controller_mutations_delete_controller(dacot):
	controllers = get_controllers(dacot)
	cid = [c[0] for c in controllers]
	qry = '''
	mutation {
		deleteController(cid: "CID")
	}
	'''.replace('CID', cid[0])
	dacot.execute(qry)
	controllers = get_controllers(dacot)
	assert len(controllers) == 0
	assert 'DemoModel' not in [c[1] for c in controllers]

def test_controller_mutations_enable_controller(dacot):
	controllers = get_controllers(dacot, show_disabled=True)
	cid = [c[0] for c in controllers]
	qry = '''
	mutation {
		enableController(cid: "CID")
	}
	'''.replace('CID', cid[0])
	dacot.execute(qry)
	controllers = get_controllers(dacot)
	assert len(controllers) > 0
	assert 'DemoModel' in [c[1] for c in controllers]
