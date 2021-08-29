import dacot_models as dm
from graphene import *
from .graphql_models import *
from fastapi.logger import logger
from graphql import GraphQLError
from copy import deepcopy
from .complex_operations import *
from datetime import datetime
import sys
import traceback

DEFAULT_VEHICLE_INTERGREEN_VALUE = 4

class CustomMutation(Mutation):
    # FIXME: Add current user to log
    # FIXME: Make log in background_task
    class Meta:
        abstract = True

    @classmethod
    def log_action(cls, msg):
        op = str(cls)
        current_user = cls.get_current_user()
        if current_user:
            email = current_user.email
        else:
            email = 'None'
        log = dm.ActionsLog(user=email, context=op, action=msg, origin="GraphQL API")
        log.save()
        logger.error(log.to_mongo().to_dict())

    @classmethod
    def generate_new_project_version(cls, proj):
        new = dm.Project.objects(id=proj.id).first()
        new.id = None
        proj.metadata.version = datetime.now().isoformat()
        new.metadata.version = 'latest'
        return proj, new

    @classmethod
    def get_current_user(cls):
        # TODO: For now, we return the same user for all requests
        return dm.User.objects(email="seed@dacot.uoct.cl").first()

    @classmethod
    def log_gql_error(cls, message):
        exc = sys.exc_info()
        if exc[2]:
            traceback.print_tb(exc[2])
        message = 'DACoT_GraphQLError: {}'.format(message)
        cls.log_action(message)
        return GraphQLError(message)

class DeleteController(CustomMutation):
    class Arguments:
        cid = NonNull(String)

    Output = String

    @classmethod
    def mutate(cls, root, info, cid):
        ctrl = dm.ControllerModel.objects(id=cid).first()
        if not ctrl:
            return cls.log_gql_error('Failed to delete controller. Controller Id {} not found'.format(cid))
        if ctrl.model == 'DEFAULT' and ctrl.company.name == 'SPEEDEVS':
            return cls.log_gql_error('Failed to delete controller. Cannot delete DEFAULT controller')
        using = dm.Project.objects(controller__model=ctrl).only('oid')
        if len(using) > 0:
            using_oid = [p.oid for p in using]
            return cls.log_gql_error('Failed to delete controller. Controller is in use by: {}'.format(using_oid))
        try:
            ctrl.disabled = True
            ctrl.save()
        except Exception as exp:
            return cls.log_gql_error('Failed to delete controller. Cause: {}'.format(str(exp)))
        return cid

class EnableController(CustomMutation):
    class Arguments:
        cid = NonNull(String)

    Output = String

    @classmethod
    def mutate(cls, root, info, cid):
        ctrl = dm.ControllerModel.objects(id=cid).first()
        if not ctrl:
            return cls.log_gql_error('Failed to enable controller. Controller Id {} not found'.format(cid))
        try:
            ctrl.disabled = False
            ctrl.save()
        except Exception as exp:
            return cls.log_gql_error('Failed to enable controller. Cause: {}'.format(str(exp)))
        cls.log_action('Controller {} enabled.'.format(cid))
        return cid

class DeleteProject(CustomMutation):
    class Arguments:
        data = GetProjectInput()

    Output = String

    @classmethod
    def mutate(cls, root, info, data):
        if data.status == "PRODUCTION":
            return cls.log_gql_error('Cannot delete a project in PRODUCTION status')
        proj = dm.Project.objects(oid=data.oid, metadata__status=data.status, metadata__version='latest').first()
        if not proj:
            return cls.log_gql_error('Project {} in status {} not found.'.format(data.oid, data.status))
        try:
            proj.delete()
        except Exception as excep:
            return cls.log_gql_error('Error deleting project {} in status {}. {}'.format(data.oid, data.status, str(excep)))
        cls.log_action('Project {} in status {} deleted.'.format(data.oid, data.status))
        return data.oid

class CreateCommune(CustomMutation):
    class Arguments:
        data = CreateCommuneInput()

    Output = Commune

    @classmethod
    def mutate(cls, root, info, data):
        commune = dm.Commune()
        commune.name = data.name
        commune.code = data.code
        if data.maintainer:
            comp = dm.ExternalCompany.objects(name=data.maintainer).first()
            if not comp:
                return cls.log_gql_error('Commune creation failed. Maintainer {} not found'.format(data.maintainer))
            commune.maintainer = comp
        if data.user_in_charge:
            user = dm.User.objects(email=data.user_in_charge).first()
            if not user:
                return cls.log_gql_error('Commune creation failed. User {} not found'.format(data.user_in_charge))
            commune.user_in_charge = user
        try:
            commune.save()
        except Exception as excep:
            return cls.log_gql_error('Error saving new commune. {}'.format(str(excep)))
        cls.log_action('Commune {} created'.format(data.name))
        return commune

class UpdateControllerModel(CustomMutation):
    class Arguments:
        data = UpdateControllerModelInput()

    Output = ControllerModel

    @classmethod
    def mutate(cls, root, info, data):
        model = dm.ControllerModel.objects(id=data.cid).first()
        if not model:
            return cls.log_gql_error('Model {} not found'.format(data.cid))
        if data.checksum:
            model.checksum = data.checksum
        if data.firmware_version:
            model.firmware_version = data.firmware_version
        try:
            model.save()
        except Exception as excep:
            return cls.log_gql_error('Failed to update model {}. {}'.format(data.cid, str(excep)))
        cls.log_action('Model {} updated.'.format(data.cid))
        return model

class CreateControllerModel(CustomMutation):
    class Arguments:
        data = CreateControllerModelInput()

    Output = ControllerModel

    @classmethod
    def mutate(cls, root, info, data):
        comp = dm.ExternalCompany.objects(name=data.company).first()
        if not comp:
            return cls.log_gql_error('Company {} not found'.format(data.company))
        model = dm.ControllerModel()
        model.company = comp
        model.model = data.model
        model.firmware_version = data.firmware_version
        model.checksum = data.checksum
        try:
            model.save()
        except Exception as excep:
            return cls.log_gql_error('Failed to save new model. {}'.format(str(excep)))
        cls.log_action('Controller {} created.'.format(data.model))
        return model

class CreatePlanParseFailedMessage(CustomMutation):
    class Arguments:
        data = CreatePlanParseFailedMessageInput()

    Output = PlanParseFailedMessage

    @classmethod
    def mutate(cls, root, info, data):
        comment = dm.Comment()
        comment.message = data.message
        comment.author = cls.get_current_user()
        failed_plan = dm.PlanParseFailedMessage()
        failed_plan.comment = comment
        failed_plan.plans = data.plans
        try:
            failed_plan.save()
        except Exception as excep:
            return cls.log_gql_error('Failed to create error message. {}'.format(str(excep)))
        cls.log_action('Error message {} created'.format(failed_plan.id))
        return failed_plan

class DeletePlanParseFailedMessage(CustomMutation):
    class Arguments:
        data = DeletePlanParseFailedMessageInput()

    Output = String

    @classmethod
    def mutate(cls, root, info, data):
        message = dm.PlanParseFailedMessage.objects(id=data.mid).first()
        if not message:
            return cls.log_gql_error('Message {} not found.'.format(data.mid))
        try:
            message.delete()
        except Exception as excep:
            return cls.log_gql_error('Failed to delete message {}. {}'.format(data.mid, str(excep)))
        cls.log_action('Message {} deleted'.format(data.mid))
        return data.mid

class DeleteCompany(CustomMutation):
    class Arguments:
        data = DeleteCompanyInput()

    Output = String

    @classmethod
    def mutate(cls, root, info, data):
        comp = dm.ExternalCompany.objects(name=data.name).first()
        if not comp:
            return cls.log_gql_error('Company {} not found'.format(data.name))
        try:
            comp.disabled = True
            comp.save()
        except Exception as excep:
            return cls.log_gql_error('Failed to delete company {}. {}'.format(data.name, str(excep)))
        cls.log_action('Company {} deleted'.format(data.name))
        return data.name

class EnableCompany(CustomMutation):
    class Arguments:
        data = DeleteCompanyInput()

    Output = String

    @classmethod
    def mutate(cls, root, info, data):
        comp = dm.ExternalCompany.objects(name=data.name).first()
        if not comp:
            return cls.log_gql_error('Company {} not found'.format(data.name))
        try:
            comp.disabled = False
            comp.save()
        except Exception as excep:
            return cls.log_gql_error('Failed to enable company {}. {}'.format(data.name, str(excep)))
        cls.log_action('Company {} enabled'.format(data.name))
        return data.name

class CreateCompany(CustomMutation):
    class Arguments:
        data = CreateCompanyInput()

    Output = ExternalCompany

    @classmethod
    def mutate(cls, root, info, data):
        comp = dm.ExternalCompany()
        comp.name = data.name
        try:
            comp.save()
        except Exception as excep:
            return cls.log_gql_error('Failed to save new company {}. {}'.format(data.name, str(excep)))
        cls.log_action('Company {} saved'.format(data.name))
        return comp

class CreateUser(CustomMutation):
    class Arguments:
        data = CreateUserInput()

    Output = User

    @classmethod
    def mutate(cls, root, info, data):
        user = dm.User()
        user.is_admin = data.is_admin
        user.full_name = data.full_name
        user.email = data.email
        user.role = data.role
        user.area = data.area
        if data.company:
            user.company = dm.ExternalCompany.objects(name=data.company).first()
            if not user.company:
                return cls.log_gql_error('Company {} not found'.format(data.company))
        try:
            user.save()
        except Exception as excep:
            return cls.log_gql_error('Failed to save user {}. {}'.format(data.email, str(excep)))
        cls.log_action('User {} created'.format(data.email))
        return user

class DeleteUser(CustomMutation):
    class Arguments:
        data = DeleteUserInput()

    Output = String

    @classmethod
    def mutate(cls, root, info, data):
        user = dm.User.objects(email=data.email).first()
        if not user:
            return cls.log_gql_error('User {} not found.'.format(data.email))
        if user.email == 'seed@dacot.uoct.cl':
            return cls.log_gql_error('Failed to delete user {}. Cannot delete SEED system user.'.format(data.email))
        commune_using = dm.Commune.objects(user_in_charge=user).only('code')
        if len(commune_using) > 0:
            using_code = [c.code for c in commune_using]
            return cls.log_gql_error('Failed to delete User. User is in use by communes: {}'.format(using_code))
        try:
            user.disabled = True
            user.save()
        except Exception as excep:
            return cls.log_gql_error('Failed to delete user {}. {}'.format(data.email, str(excep)))
        cls.log_action('User {} deleted.'.format(data.email))
        return data.email

class EnableUser(CustomMutation):
    class Arguments:
        data = DeleteUserInput()

    Output = String

    @classmethod
    def mutate(cls, root, info, data):
        user = dm.User.objects(email=data.email).first()
        if not user:
            return cls.log_gql_error('User {} not found.'.format(data.email))
        try:
            user.disabled = False
            user.save()
        except Exception as excep:
            return cls.log_gql_error('Failed to enable user {}. {}'.format(data.email, str(excep)))
        cls.log_action('User {} enabled.'.format(data.email))
        return data.email

class UpdateUser(CustomMutation):
    class Arguments:
        data = UpdateUserInput()

    Output = User

    @classmethod
    def mutate(cls, root, info, data):
        user = dm.User.objects(email=data.email).first()
        if not user:
            return cls.log_gql_error('User {} not found'.format(data.email))
        if data.is_admin:
            user.is_admin = data.is_admin
        if data.full_name:
            user.full_name = data.full_name
        try:
            user.save()
        except Exception as excep:
            return cls.log_gql_error('Failed to update user {}. {}'.format(data.email, str(excep)))
        cls.log_action('User {} updated'.format(data.email))
        return user

class UpdateCommune(CustomMutation):
    class Arguments:
        data = UpdateCommuneInput()

    Output = Commune

    @classmethod
    def mutate(cls, root, info, data):
        commune = dm.Commune.objects(code=data.code).first()
        if not commune:
            return cls.log_gql_error('Commune {} not found'.format(data.code))
        if data.maintainer:
            comp = dm.ExternalCompany.objects(name=data.maintainer).first()
            if not comp:
                return cls.log_gql_error('Company {} not found'.format(data.maintainer))
            commune.maintainer = comp
        if data.user_in_charge:
            user = dm.User.objects(email=data.user_in_charge).first()
            if not user:
                return cls.log_gql_error('User {} not found'.format(data.user_in_charge))
            commune.user_in_charge = user
        try:
            commune.save()
        except Exception as excep:
            return cls.log_gql_error('Failed to update commune {}. {}'.format(data.code, str(excep)))
        cls.log_action('Commune {} updated'.format(data.code))
        return commune

class SetDefaultVehicleIntergreen(CustomMutation):
    class Arguments:
        data = SetVehicleIntergreenInput()

    Output = String

    @classmethod
    def update_model_default(cls, data, base, proj, junc):
        veh_inters = []
        for ped_inter in junc.intergreens:
            new_inter = dm.JunctionIntergreenValue()
            new_inter.phfrom = ped_inter.phfrom
            new_inter.phto = ped_inter.phto
            new_inter.value = DEFAULT_VEHICLE_INTERGREEN_VALUE
            veh_inters.append(new_inter)
        junc.veh_intergreens = veh_inters
        junc.metadata.use_default_vi4 = True
        try:
            base.save()
            proj.save()
        except Exception as excep:
            return cls.log_gql_error('Failed to update project ({}). Cause: {}'.format(data.jid, str(excep)))
        cls.log_action('Updated DEFAULT vehicle intergreens for {}'.format(data.jid))
        return data.jid

    @classmethod
    def update_model_custom(cls, data, base, proj, junc):
        input_inters = {}
        numbers_str = list(map(str, range(0,10)))
        for phase in data.phases:
            k = [phase['phfrom'], phase['phto']]
            if k[0] in numbers_str and k[1] in numbers_str:
                k[0] = chr(int(k[0]) + 64)
                k[1] = chr(int(k[1]) + 64)
            input_inters[tuple(k)] = phase['value']
        inpl = len(input_inters)
        needed = len(junc.intergreens)
        if inpl != needed:
            return cls.log_gql_error('Missing number of phases in input. Needed {}, got {}'.format(needed, inpl))
        veh_inters = []
        for ped_inter in junc.intergreens:
            new_inter = dm.JunctionIntergreenValue()
            k = (ped_inter.phfrom, ped_inter.phto)
            if k not in input_inters:
                return cls.log_gql_error('Missing phase pair in input: {}'.format(k))
            new_inter.phfrom = ped_inter.phfrom
            new_inter.phto = ped_inter.phto
            new_inter.value = input_inters[k]
            veh_inters.append(new_inter)
        junc.veh_intergreens = veh_inters
        junc.metadata.use_default_vi4 = False
        try:
            base.save()
            proj.save()
        except Exception as excep:
            return cls.log_gql_error('Failed to update project ({}). Cause: {}'.format(data.jid, str(excep)))
        cls.log_action('Updated custom vehicle intergreens for {}'.format(data.jid))
        return data.jid

    @classmethod
    def set_vi(cls, data, is_default=True):
        oid = 'X{}0'.format(data.jid[1:-1])
        if data.status != 'PRODUCTION':
            return cls.log_gql_error('Status {} not allowed for this mutation'.format(data.status))
        proj = dm.Project.objects(oid=oid, metadata__status=data.status, metadata__version='latest').first()
        if not proj:
            return cls.log_gql_error('Project {} not found in PRODUCTION status'.format(oid))
        base, proj = cls.generate_new_project_version(proj)
        for junc in proj.otu.junctions:
            if junc.jid == data.jid:
                if is_default:
                    return cls.update_model_default(data, base, proj, junc)
                else:
                    return cls.update_model_custom(data, base, proj, junc)
        return cls.log_gql_error('Junction {} not found in project {}'.format(data.jid, oid))

    @classmethod
    def mutate(cls, root, info, data):
        return cls.set_vi(data)

class SetIntergreen(SetDefaultVehicleIntergreen):
    class Arguments:
        data = SetVehicleIntergreenInput()

    Output = String

    @classmethod
    def mutate(cls, root, info, data):
        return cls.set_vi(data, is_default=False)

class RejectProject(CustomMutation):
    class Arguments:
        data = AcceptRejectProjectInput()

    Output = String

    @classmethod
    def mutate(cls, root, info, data):
        if data.status not in ['NEW', 'UPDATE']:
            return cls.log_gql_error('Status {} not allowed for this mutation'.format(data.status))
        proj = dm.Project.objects(oid=data.oid, metadata__status=data.status, metadata__version='latest').first()
        if not proj:
            return cls.log_gql_error('Project {} in status {} not found'.format(data.oid, data.status))
        base, proj = cls.generate_new_project_version(proj)
        proj.metadata.status = 'REJECTED'
        proj.metadata.version = datetime.now().isoformat()
        try:
            base.save()
            proj.save()
        except Exception as excep:
            return cls.log_gql_error('Failed to reject project {} {}. {}'.format(data.oid, data.status, str(excep)))
        cls.log_action('Project {} {} REJECTED'.format(data.oid, data.status))
        email = EmailSender(info.context)
        if proj.metadata.status == 'UPDATE': 
            send_success, error = email.send_update_rejected(proj, data.message, data.img)
        else:
            send_success, error = email.send_new_rejected(proj, data.message, data.img)
        if send_success:
            cls.log_action('Notifications for project {} {} sent'.format(proj.oid, proj.metadata.status))
        else:
            cls.log_gql_error('Failed to send notifications for project {} {}. {}'.format(proj.oid, proj.metadata.status, error))
        return data.oid

class AcceptProject(CustomMutation):
    class Arguments:
        data = AcceptRejectProjectInput()

    Output = String

    @classmethod
    def accept_update(cls, data, proj):
        base = dm.Project.objects(oid=data.oid, metadata__status='PRODUCTION', metadata__version='latest').first()
        if not base:
            return cls.log_gql_error('Failed to accept UPDATE for {}. Base version not found'.format(data.oid))
        base.metadata.version = datetime.now().isoformat()
        proj.metadata.status = 'PRODUCTION'
        try:
            base.save()
            proj.save()
        except Exception as excep:
            return cls.log_gql_error('Failed to accept UPDATE for {}. {}'.format(data.oid, str(excep)))
        cls.log_action('UPDATE for {} ACCEPTED'.format(data.oid))
        return data.oid

    @classmethod
    def accept_new(cls, data, proj):
        proj.metadata.status = 'PRODUCTION'
        try:
            proj.save()
        except Exception as excep:
            return cls.log_gql_error('Failed to accept NEW project {}. {}'.format(data.oid, str(excep)))
        cls.log_action('NEW project {} ACCEPTED'.format(data.oid))
        return data.oid

    @classmethod
    def mutate(cls, root, info, data):
        if data.status not in ['NEW', 'UPDATE']:
            return cls.log_gql_error('Status {} not allowed for this mutation'.format(data.status))
        proj = dm.Project.objects(oid=data.oid, metadata__status=data.status, metadata__version='latest').first()
        if not proj:
            return cls.log_gql_error('Project {} in status {} not found'.format(data.oid, data.status))
        email = EmailSender(info.context)
        if data.status == 'UPDATE':
            op_res = cls.accept_update(data, proj)
            send_success, error = email.send_update_accepted(proj, data.message, data.img)
        else:
            op_res = cls.accept_new(data, proj)
            send_success, error = email.send_new_accepted(proj, data.message, data.img)
        if send_success:
            cls.log_action('Notifications for project {} {} sent'.format(proj.oid, proj.metadata.status))
        else:
            cls.log_gql_error('Failed to send notifications for project {} {}. {}'.format(proj.oid, proj.metadata.status, error))
        return op_res

class CreateUpdateProject(CustomMutation):
    class Arguments:
        data = CreateProjectInput()

    Output = String

    @classmethod
    def mutate(cls, root, info, data):
        parser = ProjectInputToProject(cls.get_current_user())
        success, parsed_or_error_msg = parser.parse(data)
        if not success:
            return cls.log_gql_error('Failed to parse project input: {}'.format(parsed_or_error_msg))
        parsed = parsed_or_error_msg
        if parsed.metadata.status not in ['NEW', 'UPDATE']:
            return cls.log_gql_error('Status {} is not allowed for this mutation'.format(parsed.metadata.status))
        existing_new = dm.Project.objects(oid=parsed.oid, metadata__status='NEW', metadata__version='latest')
        if existing_new:
            return cls.log_gql_error('Project {} already exists in status NEW'.format(data.oid))
        existing_update = dm.Project.objects(oid=parsed.oid, metadata__status='UPDATE', metadata__version='latest')
        if existing_update:
            return cls.log_gql_error('Project {} already exists in status UPDATE'.format(data.oid))
        if parsed.metadata.status == 'UPDATE':
            base = dm.Project.objects(oid=data.oid, metadata__status='PRODUCTION', metadata__version='latest').first()
            if not base:
                return cls.log_gql_error('Failed to create UPDATE, base version for {} not found'.format(data.oid))
        try:
            parsed.save()
        except Exception as excep:
            return cls.log_gql_error('Failed to save project {} {}. {}'.format(parsed.oid, parsed.metadata.status, str(excep)))
        cls.log_action('Project {} {} saved'.format(parsed.oid, parsed.metadata.status))
        email = EmailSender(info.context)
        if parsed.metadata.status == 'UPDATE': 
            send_success, error = email.send_update_created(parsed)
        else:
            send_success, error = email.send_new_created(parsed)
        if send_success:
            cls.log_action('Notifications for project {} {} sent'.format(parsed.oid, parsed.metadata.status))
        else:
            cls.log_gql_error('Failed to send notifications for project {} {}. {}'.format(parsed.oid, parsed.metadata.status, error))
        return parsed.id

class ComputeTimingTables(CustomMutation):
    class Arguments:
        data = GetProjectInput()

    Output = Boolean

    @classmethod
    def mutate(cls, root, info, data):
        if data.status != 'PRODUCTION':
            return cls.log_gql_error('Status {} not allowed for this mutation'.format(data.status))
        proj = dm.Project.objects(oid=data.oid, metadata__status=data.status, metadata__version='latest').first()
        if not proj:
            return cls.log_gql_error('Project {} in status {} not found'.format(data.oid, data.status))
        base, proj = cls.generate_new_project_version(proj)
        try:
            compute = ComputeJunctionPlansTables(proj)
            proj = compute.run()
        except Exception as excep:
            return cls.log_gql_error('Failed to compute tables for {}. {}'.format(data.oid, str(excep)))
        try:
            base.save()
            proj.save()
        except Exception as excep:
            return cls.log_gql_error('Failed to save computed timings for {}. {}'.format(data.oid, str(excep)))
        cls.log_action('Saved computed timings for {}'.format(data.oid))
        return True
