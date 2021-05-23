import logging
from graphene import *
from graphql_mutations import *
from graphql_queries import *

class Mutation(ObjectType):
    # Project
    delete_project = DeleteProject.Field()
    # Commune
    create_commune = CreateCommune.Field()
    # ControllerModel
    delete_controller = DeleteController.Field()
    update_controller = UpdateControllerModel.Field()
    create_controller = CreateControllerModel.Field()

dacot_schema = Schema(query=Query, mutation=Mutation)

class GraphQLLogFilter(logging.Filter):
    def filter(self, record):
        if "graphql.error.located_error.GraphQLLocatedError:" in record.msg:
            return False
        return True

# Disable graphene logging
logging.getLogger("graphql.execution.utils").addFilter(GraphQLLogFilter())
