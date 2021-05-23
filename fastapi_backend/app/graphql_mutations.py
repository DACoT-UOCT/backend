import dacot_models as dm
from graphene import *
from graphql_models import *
from fastapi.logger import logger
from graphql import GraphQLError

class CustomMutation(Mutation):
    # FIXME: Send emails functions
    # FIXME: Add current user to log
    # FIXME: Make log in background_task
    class Meta:
        abstract = True

    @classmethod
    def log_action(cls, msg, is_error=False):
        op = str(cls)
        current_user = cls.get_current_user()
        if current_user:
            email = current_user.email
        else:
            email = 'None'
        log = dm.ActionsLog(user=email, context=op, action=msg, origin="GraphQL API")
        log.save()
        if is_error:
            logger.error(log.to_mongo().to_dict())
        else:
            logger.info(log.to_mongo().to_dict())

    @classmethod
    def get_current_user(cls):
        # Returns the currently logged user
        # TODO: FIXME: For now, we return the same user for all requests
        return dm.User.objects(email="seed@dacot.uoct.cl").first()

    @classmethod
    def log_gql_error(cls, message):
        message = 'DACoT_GraphQLError: {}'.format(message)
        cls.log_action(message, is_error=True)
        return GraphQLError(message)

    @classmethod
    def get_b64file_data(cls, base64data):
        _, filedata = base64data.split(",")
        b64bytes = base64.b64decode(filedata)
        mime = magic.from_buffer(b64bytes[0:2048], mime=True)
        return b64bytes, mime

class DeleteController(CustomMutation):
    class Arguments:
        cid = NonNull(String)

    Output = String

    @classmethod
    def mutate(cls, root, info, cid):
        ctrl = dm.ControllerModel.objects(id=cid).first()
        if not ctrl:
            return cls.log_gql_error('Failed to delete controller. Controller Id {} not found'.format(cid))
        try:
            ctrl.delete()
        except Exception as exp:
            return cls.log_gql_error('Failed to delete controller. Cause: {}'.format(str(exp)))
        return cid

class DeleteProject(CustomMutation):
    class Arguments:
        detail = GetProjectInput()

    Output = String

    @classmethod
    def mutate(cls, root, info, detail):
        if detail.status == "PRODUCTION":
            return cls.log_gql_error('Cannot delete a project in PRODUCTION status')
        proj = dm.Project.objects(oid=detail.oid, metadata__status=detail.status).first()
        if not proj:
            return cls.log_gql_error('Project {} in status {} not found.'.format(detail.oid, detail.status))
        try:
            proj.delete()
        except Exception as excep:
            return cls.log_gql_error('Error deleting project {} in status {}. {}'.format(detail.oid, detail.status, str(excep)))
        cls.log_action('Project {} in status {} deleted.'.format(detail.oid, detail.status))
        return detail.oid

class CreateCommune(CustomMutation):
    class Arguments:
        detail = CreateCommuneInput()

    Output = Commune

    @classmethod
    def mutate(cls, root, info, detail):
        commune = dm.Commune()
        commune.name = detail.name
        commune.code = detail.code
        if detail.maintainer:
            comp = dm.ExternalCompany.objects(name=detail.maintainer).first()
            if not comp:
                return cls.log_gql_error('Commune creation failed. Maintainer {} not found'.format(detail.maintainer))
            commune.maintainer = comp
        if detail.user_in_charge:
            user = dm.User.objects(email=detail.user_in_charge).first()
            if not user:
                return cls.log_gql_error('Commune creation failed. User {} not found'.format(detail.user_in_charge))
            commune.user_in_charge = user
        try:
            commune.save()
        except Exception as excep:
            return cls.log_gql_error('Error saving new commune. {}'.format(str(excep)))
        cls.log_action('Commune {} created'.format(detail.name))
        return commune

class UpdateControllerModel(CustomMutation):
    class Arguments:
        detail = UpdateControllerModelInput()

    Output = ControllerModel

    @classmethod
    def mutate(cls, root, info, detail):
        model = dm.ControllerModel.objects(id=detail.cid).first()
        if not model:
            return cls.log_gql_error('Model {} not found'.format(detail.cid))
        if detail.checksum:
            model.checksum = detail.checksum
        if detail.firmware_version:
            model.firmware_version = detail.firmware_version
        try:
            model.save()
        except Exception as excep:
            return cls.log_gql_error('Failed to update model {}. {}'.format(detail.cid, str(excep)))
        cls.log_action('Model {} updated.'.format(detail.cid))
        return model

class CreateControllerModel(CustomMutation):
    class Arguments:
        detail = CreateControllerModelInput()

    Output = ControllerModel

    @classmethod
    def mutate(cls, root, info, detail):
        comp = dm.ExternalCompany.objects(name=detail.company).first()
        if not comp:
            return cls.log_gql_error('Company {} not found'.format(detail.company))
        model = dm.ControllerModel()
        model.company = comp
        model.model = detail.model
        model.firmware_version = detail.firmware_version
        model.checksum = detail.checksum
        try:
            model.save()
        except Exception as excep:
            return cls.log_gql_error('Failed to save new model. {}'.format(str(excep)))
        cls.log_action('Model "{}" created'.format(controller_details.model))
        return model
