import json
from fastapi import FastAPI, Request, Depends
from fastapi.logger import logger
from fastapi.encoders import jsonable_encoder
from mongoengine import connect
from starlette.datastructures import URL
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import HTMLResponse, RedirectResponse, Response
from authlib.integrations.starlette_client import OAuth, OAuthError
from google.oauth2 import id_token
from google.auth.transport import requests as GoogleAuthReq
from pydantic import BaseModel
import dacot_models as dm

from .config import get_settings
from .custom_graphql_app import CustomGraphQLApp
from .db_init import DBInit
from .graphql_schema import dacot_schema

connect(host=get_settings().mongo_uri)
db_init = DBInit(get_settings().apikey_users_file)
db_init.init()

api_description = """
API del proyecto Datos Abiertos para el Control de Tránsito
(DACoT) desarrollado por SpeeDevs en colaboración con la Unidad Operativa de
Control de Tránsito (UOCT) de la región Metropolitana en el contexto de la
XXVIII Feria de Software del Departamento de Informática en la Universidad
Técnica Federico Santa María.
"""

app = FastAPI(title="DACoT API", version="v0.2", description=api_description)


graphql_app = CustomGraphQLApp(schema=dacot_schema)


@app.get("/")
async def graphiql(request: Request):
    request._url = URL("/graphql")
    return await graphql_app.handle_graphiql(request=request)


@app.post("/")
async def graphql(request: Request):
    return await graphql_app.handle_graphql(request=request)


@app.post("/graphql")
async def graphql(request: Request):
    return await graphql_app.handle_graphql(request=request)


logger.warning("App Ready")

class User(BaseModel):
    email: str = None
    is_admin: bool = False
    disabled: bool = True
    rol: str = None
    area: str = None
    full_name: str = None

app.add_middleware(SessionMiddleware, secret_key=get_settings().authjwt_secret_key, same_site='None', https_only=True, max_age=2592000)

gconfig = Config('.env')
oauth = OAuth(gconfig)

oauth.register(name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

def get_user_from_token(token):
    return id_token.verify_oauth2_token(token, GoogleAuthReq.Request())

def create_new_session(email):
    s = dm.ActiveUserSession(email=email).first()
    if not s:
        s = dm.ActiveUserSession()
        s.email = email
    s.valid = True
    s.save()

def destroy_session(email):
    s = dm.ActiveUserSession(email=email).first()
    if not s:
        return
    s.valid = False
    s.save()

def check_session(email):
    s = dm.ActiveUserSession(email=email).first()
    if not s:
        return False
    return s.valid

@app.post('/swap_token')
async def swap(request: Request):
    gtoken = jsonable_encoder(await request.body())
    try:
        user = get_user_from_token(gtoken)
    except Exception as ex:
        return Response('', status_code=500)
    if not (user['email'] and user['email_verified']):
        return Response('Invalid email data', status_code=422)
    create_new_session(user['email'])
    request.session['user'] = dict(user)

@app.get('/logout')
async def logout(request: Request):
    if 'user' in request.session:
        u = request.session['user']
        destroy_session(u['email'])
    request.session.pop('user', None)

@app.get('/me')
async def me(request: Request):
    if 'user' not in request.session:
        return Response(None, status_code=404)
    u = request.session['user']
    dbu = dm.User.objects(email=u['email']).first()
    if not dbu:
        return Response(None, status_code=404)
    if dbu.disabled:
        return Response(None, status_code=422)
    r = User(**dbu.to_mongo())
    if not check_session(r['email']):
        return Response(None, status_code=404)
    return r

logger.warning("Security Ready")
