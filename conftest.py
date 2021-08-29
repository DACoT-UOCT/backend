import os
import pytest
import mongomock
from graphene.test import Client as GQLClient

os.environ['mongo_uri'] = 'mongomock://127.0.0.1/db'
os.environ['mail_user'] = ''
os.environ['mail_pass'] = ''
os.environ['apikey_users_file'] = './fastapi_backend/app/fake_users.json'
	
from fastapi_backend.app.main import app, dacot_schema

@pytest.fixture(scope='session')

def dacot(request):
	return GQLClient(schema=dacot_schema)
