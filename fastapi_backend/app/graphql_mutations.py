import dacot_models as dm
from graphene import *
from graphql_models import *

class CustomMutation(Mutation):
    # FIXME: Send emails functions
    # FIXME: Add current user to log
    # FIXME: Make log in background_task
    class Meta:
        abstract = True

    @classmethod
    def log_action(cls, msg, graphql_info, is_error=False):
        op = str(graphql_info.operation)
        current_user = cls.get_current_user()
        if current_user:
            email = current_user.email
        else:
            email = 'None'
        log = dm.ActionsLog(user=email, context=op, action=msg, origin="GraphQL API")
        log.save()
        if is_error:
            pass
        else:
            pass

    @classmethod
    def get_current_user(cls):
        # Returns the currently logged user
        # TODO: FIXME: For now, we return the same user for all requests
        return UserModel.objects(email="seed@dacot.uoct.cl").first()

    @classmethod
    def log_gql_error(cls, message, info):
        cls.log_action(message, info, is_error=True)
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
