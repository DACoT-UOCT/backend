from graphene import *
import dacot_models as dm
from graphene_mongo import MongoengineObjectType, MongoengineConnectionField

import mongoengine
mongoengine.connect('db', host='mongomock://127.0.0.1')

user = dm.User(full_name='Carlos Ponce', email='cponce@example.org', role='Empresa', area='TIC')
user.save()
otu = dm.OTU(oid='X001110', junctions=[dm.Junction(jid='J001111', metadata=dm.JunctionMeta(sales_id=1, location=[0, 0]))])

for i in range(50):
    oid = 'X001{:02d}0'.format(i)
    proj = dm.Project(oid=oid, metadata=dm.ProjectMeta(status='NEW', status_user=user), otu=otu)
    proj.save()

class Project(MongoengineObjectType):
    class Meta:
        model = dm.Project
        interfaces = (Node,)

class Query(ObjectType):
    projects = MongoengineConnectionField(Project, metadata__status=NonNull(String), metadata__version=NonNull(String))

schema = Schema(query=Query)

result = schema.execute('query { projects(metadata_Status: "NEW", metadata_Version: "latest", first: 2) { edges { node { oid } cursor } pageInfo { hasNextPage endCursor } } }')
print(result)
