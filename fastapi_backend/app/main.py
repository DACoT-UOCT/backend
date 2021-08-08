import json
from fastapi import FastAPI, Request, Depends
from fastapi.logger import logger
from mongoengine import connect
from starlette.datastructures import URL
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import HTMLResponse, RedirectResponse
from authlib.integrations.starlette_client import OAuth, OAuthError

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

app.add_middleware(SessionMiddleware, secret_key="!secret")

gconfig = Config('.env')
oauth = OAuth(gconfig)

oauth.register(name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

@app.get('/home')
async def homepage(request: Request):
    user = request.session.get('user')
    print(user)
    if user:
        data = json.dumps(user)
        html = f'<pre>{data}</pre><a href="/logout">logout</a>'
        return HTMLResponse(html)
    return HTMLResponse('<a href="/login">login</a>')

@app.get('/login')
async def login(request: Request):
    # redirect_uri = request.url_for('auth')
    redirect_uri = 'http://localhost:8081/auth'
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get('/auth')
async def auth(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as error:
        return HTMLResponse(f'<h1>{error.error}</h1>')
    user = await oauth.google.parse_id_token(request, token)
    request.session['user'] = dict(user)
    return RedirectResponse(url='/home')


@app.get('/logout')
async def logout(request: Request):
    request.session.pop('user', None)
    return RedirectResponse(url='/home')

logger.warning("Security Ready")
