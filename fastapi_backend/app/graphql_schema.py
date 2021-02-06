import logging
import graphene
from graphene.relay import Node
from graphene_mongo import MongoengineObjectType
from models import User as UserModel
from models import ExternalCompany as ExternalCompanyModel
from models import ActionsLog as ActionsLogModel
from models import Commune as CommuneModel
from models import Project as ProjectModel
from models import Comments as CommentsModel
from models import PlanParseFailedMessage as PlanParseFailedMessageModel
from mongoengine import ValidationError, NotUniqueError
from graphql import GraphQLError

class CustomMutation(graphene.Mutation):
    # TODO: FIXME: Send emails functions
    # TODO: FIXME: Add current user to log
    # TODO: FIXME: Make log in background_task
    class Meta:
        abstract = True

    @classmethod
    def log_action(cls, message, graphql_info):
        op = str(graphql_info.operation)
        log = ActionsLogModel(user='None', context=op, action=message, origin='GraphQL API')
        log.save()

class Comment(MongoengineObjectType):
    class Meta:
        model = CommentModel
        interfaces = (Node,)

class PlanParseFailedMessage(MongoengineObjectType):
    class Meta:
        model = PlanParseFailedMessageModel
        interfaces = (Node,)

class PartialPlanParseFailedMessage(graphene.ObjectType):
    mid = graphene.NonNull(graphene.String)
    date = graphene.NonNull(graphene.DateTime)
    message = graphene.NonNull(graphene.String)

class ExternalCompany(MongoengineObjectType):
    class Meta:
        model = ExternalCompanyModel
        interfaces = (Node,)

class User(MongoengineObjectType):
    class Meta:
        model = UserModel
        interfaces = (Node,)

class ActionsLog(MongoengineObjectType):
    class Meta:
        model = ActionsLogModel
        interfaces = (Node,)

class Commune(MongoengineObjectType):
    class Meta:
        model = CommuneModel
        interfaces = (Node,)

class JunctionCoordinates(graphene.ObjectType):
    jid = graphene.NonNull(graphene.String)
    latitude = graphene.NonNull(graphene.Float)
    longitude = graphene.NonNull(graphene.Float)

class Query(graphene.ObjectType):
    users = graphene.List(User)
    user = graphene.Field(User, email=graphene.NonNull(graphene.String))
    actions_logs = graphene.List(ActionsLog)
    actions_log = graphene.Field(ActionsLog, logid=graphene.NonNull(graphene.String))
    communes = graphene.List(Commune)
    companies = graphene.List(ExternalCompany)
    junctions_coordinates = graphene.List(JunctionCoordinates)
    failed_plans = graphene.List(PartialPlanParseFailedMessage)
    failed_plan = graphene.Field(PlanParseFailedMessage, mid=graphene.NonNull(graphene.String))

    def resolve_failed_plans(self, info):
        return list(PlanParseFailedMessageModel.objects.only('id', 'date', 'message').all())

    def resolve_failed_plan(self, info, mid):
        return PlanParseFailedMessageModel.objects(id=mid).first()

    def resolve_junctions_coordinates(self, info):
        coords = []
        filter1 = 'otu.junctions.id'
        filter2 = 'otu.junctions.metadata.location'
        locations = ProjectModel.objects.only(filter1, filter2).all()
        for project in locations:
            for junction in project.otu.junctions:
                coords.append({
                    'jid': junction.jid,
                    'latitude': junction.metadata.location['coordinates'][0],
                    'longitude': junction.metadata.location['coordinates'][1]
                })
        return coords

    def resolve_companies(self, info):
        return list(ExternalCompany.objects.all())

    def resolve_communes(self, info):
        return list(CommuneModel.objects.all())

    def resolve_actions_logs(self, info):
        return list(ActionsLogModel.objects.all())

    def resolve_actions_log(self, info, logid):
        return ActionsLogModel.objects(id=logid).first()

    def resolve_users(self, info):
        return list(UserModel.objects.all())

    def resolve_user(self, info, email):
        return UserModel.objects(email=email).first()

class UpdateCommuneInput(graphene.InputObjectType):
    code = graphene.NonNull(graphene.Int)
    maintainer = graphene.String()
    user_in_charge = graphene.String()

class UpdateCommune(CustomMutation):
    class Arguments:
        commune_details = UpdateCommuneInput()

    Output = Commune

    @classmethod
    def mutate(cls, root, info, commune_details):
        commune = CommuneModel.objects(code=commune_details.code).first()
        if not commune:
            cls.log_action('Failed to update commune "{}". Commune not found'.format(commune_details.code), info)
            return GraphQLError('Commune "{}" not found'.format(commune_details.code))
        if commune_details.maintainer != None:
            maintainer = ExternalCompanyModel.objects(name=commune_details.maintainer).first()
            if not maintainer:
                cls.log_action('Failed to update commune "{}". Maintainer "{}" not found'.format(commune_details.code, commune_details.maintainer), info)
                return GraphQLError('Maintainer "{}" not found'.format(commune_details.maintainer))
            commune.maintainer = maintainer
        if commune_details.user_in_charge != None:
            user = UserModel.objects(email=commune_details.user_in_charge).first()
            if not user:
                cls.log_action('Failed to update commune "{}". User "{}" not found'.format(commune_details.code, commune_details.user_in_charge), info)
                return GraphQLError('User "{}" not found'.format(commune_details.user_in_charge))
            commune.user_in_charge = user
        try:
            commune.save()
        except ValidationError as excep:
            cls.log_action('Failed to update commune "{}". {}'.format(commune.name, excep), info)
            return GraphQLError(excep)
        cls.log_action('Commune "{}" updated.'.format(commune.name), info)
        return commune

class CreateUserInput(graphene.InputObjectType):
    is_admin = graphene.NonNull(graphene.Boolean)
    full_name = graphene.NonNull(graphene.String)
    email = graphene.NonNull(graphene.String)
    role = graphene.NonNull(graphene.String)
    area = graphene.NonNull(graphene.String)
    company = graphene.String()

class CreateUser(CustomMutation):
    class Arguments:
        user_details = CreateUserInput()

    Output = User

    @classmethod
    def mutate(cls, root, info, user_details):
        user = UserModel()
        user.is_admin = user_details.is_admin
        user.full_name = user_details.full_name
        user.email = user_details.email
        user.role = user_details.role
        user.area = user_details.area
        if user_details.company:
            user.company = ExternalCompanyModel.objects(name=user_details.company).first()
            if not user.company:
                cls.log_action('Failed to create user "{}". ExternalCompany "{}" not found'.format(user.email, user_details.company), info)
                return GraphQLError('ExternalCompany "{}" not found'.format(user_details.company))
        try:
            user.save()
        except (ValidationError, NotUniqueError) as excep:
            cls.log_action('Failed to create user "{}". {}'.format(user.email, excep), info)
            return GraphQLError(excep)
        cls.log_action('User "{}" created'.format(user.email), info)
        return user

class DeleteUserInput(graphene.InputObjectType):
    email = graphene.NonNull(graphene.String)

class DeleteUser(CustomMutation):
    class Arguments:
        user_details = DeleteUserInput()

    Output = graphene.String

    @classmethod
    def mutate(cls, root, info, user_details):
        user = UserModel.objects(email=user_details.email).first()
        if not user:
            cls.log_action('Failed to delete user "{}". User not found'.format(user_details.email), info)
            return GraphQLError('User "{}" not found'.format(user_details.email))
        uid = user.id
        user.delete()
        cls.log_action('User "{}" deleted'.format(user_details.email), info)
        return uid

class UpdateUserInput(graphene.InputObjectType):
    email = graphene.NonNull(graphene.String)
    is_admin = graphene.Boolean()
    full_name = graphene.String()

class UpdateUser(CustomMutation):
    class Arguments:
        user_details = UpdateUserInput()

    Output = User

    @classmethod
    def mutate(cls, root, info, user_details):
        user = UserModel.objects(email=user_details.email).first()
        if not user:
            cls.log_action('Failed to update user "{}". User not found'.format(user_details.email), info)
            return GraphQLError('User "{}" not found'.format(user_details.email))
        if user_details.is_admin != None:
            user.is_admin = user_details.is_admin
        if user_details.full_name != None:
            user.full_name = user_details.full_name
        try:
            user.save()
        except ValidationError as excep:
            cls.log_action('Failed to update user "{}". {}'.format(user_details.email, excep), info)
            return GraphQLError(excep)
        cls.log_action('User "{}" updated.'.format(user_details.email), info)
        return user

class CreateCompanyInput(graphene.InputObjectType):
    name = graphene.NonNull(graphene.String)

class CreateCompany(CustomMutation):
    class Arguments:
        company_details = CreateCompanyInput()

    Output = ExternalCompany

    @classmethod
    def mutate(cls, root, info, company_details):
        company = ExternalCompanyModel()
        company.name = company_details.name
        try:
            company.save()
        except (ValidationError, NotUniqueError) as excep:
            cls.log_action('Failed to create company "{}". {}'.format(company_details.name, excep), info)
            return GraphQLError(excep)
        cls.log_action('Company "{}" created'.format(company.name), info)
        return company

class DeleteCompanyInput(graphene.InputObjectType):
    name = graphene.NonNull(graphene.String)

class DeleteCompany(CustomMutation):
    class Arguments:
        company_details = DeleteCompanyInput()

    Output = graphene.String

    @classmethod
    def mutate(cls, root, info, company_details):
        company = ExternalCompanyModel.objects(name=company_details.name).first()
        if not company:
            cls.log_action('Failed to delete company "{}". Company not found'.format(company_details.name), info)
            return GraphQLError('Company "{}" not found'.format(company_details.name))
        cid = company.id
        company.delete()
        cls.log_action('Company "{}" deleted'.format(company_details.name), info)
        return cid

class DeletePlanParseFailedMessageInput(graphene.InputObjectType):
    mid = graphene.NonNull(graphene.String)

class DeletePlanParseFailedMessage(CustomMutation):
    class Arguments:
        message_details = DeletePlanParseFailedMessageInput()

    Output = graphene.String

    @classmethod
    def mutate(cls, root, info, message_details):
        message = PlanParseFailedMessageModel.objects(id=message_details.mid).first()
        if not message:
            cls.log_action('Failed to delete parse failed message "{}". Message not found'.format(message_details.mid), info)
            return GraphQLError('Message "{}" not found'.format(message_details.mid))
        mid = message.mid
        message.delete()
        cls.log_action('Message "{}" deleted'.format(message_details.mid), info)
        return mid

class Mutation(graphene.ObjectType):
    create_user = CreateUser.Field()
    delete_user = DeleteUser.Field()
    update_user = UpdateUser.Field()
    update_commune = UpdateCommune.Field()
    create_company = CreateCompany.Field()
    delete_company = DeleteCompany.Field()
    delete_failed_plan = DeletePlanParseFailedMessage.Field()

dacot_schema = graphene.Schema(query=Query, mutation=Mutation)

class GraphQLLogFilter(logging.Filter):
    def filter(self, record):
        if 'graphql.error.located_error.GraphQLLocatedError:' in record.msg:
            return False
        return True

# Disable graphene logging
logging.getLogger('graphql.execution.utils').addFilter(GraphQLLogFilter())
