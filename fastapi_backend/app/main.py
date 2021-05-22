from fastapi import FastAPI, Request, Depends
from fastapi.logger import logger
from fastapi_jwt_auth import AuthJWT
from mongoengine import connect
from starlette.datastructures import URL

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


@AuthJWT.load_config
def get_config():
    return get_settings()


graphql_app = CustomGraphQLApp(schema=dacot_schema)


@app.get("/")
async def graphiql(request: Request):
    request._url = URL("/graphql")
    return await graphql_app.handle_graphiql(request=request)


@app.post("/")
async def graphql(request: Request, authorize: AuthJWT = Depends()):
    request.state.authorize = authorize
    return await graphql_app.handle_graphql(request=request)


@app.post("/graphql")
async def graphql(request: Request, authorize: AuthJWT = Depends()):
    request.state.authorize = authorize
    return await graphql_app.handle_graphql(request=request)


logger.warning("App Ready")
