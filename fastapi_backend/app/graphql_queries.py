from graphene import *

class Query(ObjectType):
    users = List(String)
