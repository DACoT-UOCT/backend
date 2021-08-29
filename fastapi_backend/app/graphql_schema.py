import logging
from graphene import *
from .graphql_mutations import *
from .graphql_queries import *
from .graphql_models import *

class Mutation(ObjectType):
    # Project
    delete_project = DeleteProject.Field()
    reject_project = RejectProject.Field()
    accept_project = AcceptProject.Field()
    create_project = CreateUpdateProject.Field()
    update_project = CreateUpdateProject.Field()
    # Commune
    create_commune = CreateCommune.Field()
    update_commune = UpdateCommune.Field()
    # ControllerModel
    delete_controller = DeleteController.Field()
    enable_controller = EnableController.Field()
    update_controller = UpdateControllerModel.Field()
    create_controller = CreateControllerModel.Field()
    # FailedPlans
    create_failed_plan = CreatePlanParseFailedMessage.Field()
    delete_failed_plan = DeletePlanParseFailedMessage.Field()
    # Company
    delete_company = DeleteCompany.Field()
    create_company = CreateCompany.Field()
    enable_company = EnableCompany.Field()
    # User
    create_user = CreateUser.Field()
    delete_user = DeleteUser.Field()
    update_user = UpdateUser.Field()
    enable_user = EnableUser.Field()
    # Vehicle Intergreens
    set_default_veh_intergreen = SetDefaultVehicleIntergreen.Field()
    set_veh_intergreen = SetIntergreen.Field()
    # Plans
    compute_tables = ComputeTimingTables.Field()

dacot_schema = Schema(query=Query, mutation=Mutation, types=[User])

class GraphQLLogFilter(logging.Filter):
    def filter(self, record):
        if "graphql.error.located_error.GraphQLLocatedError:" in record.msg:
            return False
        return True

# Disable graphene logging
logging.getLogger("graphql.execution.utils").addFilter(GraphQLLogFilter())
