import magic
import base64
import logging
from datetime import datetime

import graphene
import magic
from dacot_models import APIKeyUsers as APIKeyUsersModel
from dacot_models import ActionsLog as ActionsLogModel
from dacot_models import Comment as CommentModel
from dacot_models import Commune as CommuneModel
from dacot_models import Controller as ProjControllerModel
from dacot_models import ControllerModel as ControllerModelModel
from dacot_models import ExternalCompany as ExternalCompanyModel
from dacot_models import HeaderItem as ProjectHeaderItemModel
from dacot_models import Junction as JunctionModel
from dacot_models import JunctionIntergreenValue as JunctionIntergreenValueModel
from dacot_models import JunctionMeta as JunctionMetaModel
from dacot_models import JunctionPhaseSequenceItem as JunctionPhaseSequenceItemModel
from dacot_models import JunctionPlan as JunctionPlanModel
from dacot_models import JunctionPlanIntergreenValue as JunctionPlanIntergreenValueModel
from dacot_models import JunctionPlanPhaseValue as JunctionPlanPhaseValueModel
from dacot_models import OTU as OTUModel
from dacot_models import OTUMeta as OTUMetaModel
from dacot_models import OTUProgramItem as OTUProgramItemModel
from dacot_models import PlanParseFailedMessage as PlanParseFailedMessageModel
from dacot_models import Poles as PolesModel
from dacot_models import Project as ProjectModel
from dacot_models import ProjectMeta as ProjectMetaModel
from dacot_models import UPS as UPSModel
from dacot_models import User as UserModel
from fastapi.logger import logger
from graphene_mongo import MongoengineObjectType, MongoengineConnectionField
from graphql import GraphQLError
from mongoengine import ValidationError, NotUniqueError


class JunctionIntergreenValue(MongoengineObjectType):
    class Meta:
        model = JunctionIntergreenValueModel


class JunctionPhaseSequenceItem(MongoengineObjectType):
    class Meta:
        model = JunctionPhaseSequenceItemModel


class Controller(MongoengineObjectType):
    class Meta:
        model = ProjControllerModel


class HeaderItem(MongoengineObjectType):
    class Meta:
        model = ProjectHeaderItemModel


class UPS(MongoengineObjectType):
    class Meta:
        model = UPSModel


class Poles(MongoengineObjectType):
    class Meta:
        model = PolesModel


class Project(MongoengineObjectType):
    class Meta:
        model = ProjectModel
        interfaces = (graphene.relay.Node,)


class ProjectMeta(MongoengineObjectType):
    class Meta:
        model = ProjectMetaModel


class JunctionMeta(MongoengineObjectType):
    class Meta:
        model = JunctionMetaModel


class JunctionPlan(MongoengineObjectType):
    class Meta:
        model = JunctionPlanModel


class JunctionPlanPhaseValue(MongoengineObjectType):
    class Meta:
        model = JunctionPlanPhaseValueModel


class JunctionPlanIntergreenValue(MongoengineObjectType):
    class Meta:
        model = JunctionPlanIntergreenValueModel


class Junction(MongoengineObjectType):
    class Meta:
        model = JunctionModel


class Comment(MongoengineObjectType):
    class Meta:
        model = CommentModel


class PlanParseFailedMessage(MongoengineObjectType):
    class Meta:
        model = PlanParseFailedMessageModel


class PartialPlanParseFailedMessage(graphene.ObjectType):
    id = graphene.NonNull(graphene.String)
    date = graphene.NonNull(graphene.DateTime)
    comment = graphene.NonNull(Comment)


class ExternalCompany(MongoengineObjectType):
    class Meta:
        model = ExternalCompanyModel


class User(MongoengineObjectType):
    class Meta:
        model = UserModel


class ActionsLog(MongoengineObjectType):
    class Meta:
        model = ActionsLogModel


class Commune(MongoengineObjectType):
    class Meta:
        model = CommuneModel


class ControllerModel(MongoengineObjectType):
    class Meta:
        model = ControllerModelModel


class OTU(MongoengineObjectType):
    class Meta:
        model = OTUModel


class OTUMeta(MongoengineObjectType):
    class Meta:
        model = OTUMetaModel


class OTUProgramItem(MongoengineObjectType):
    class Meta:
        model = OTUProgramItemModel


class PartialVersionInfo(graphene.ObjectType):
    vid = graphene.NonNull(graphene.String)
    date = graphene.NonNull(graphene.DateTime)
    comment = graphene.Field(Comment)


class CustomMutation(graphene.Mutation):
    # TODO: FIXME: Send emails functions
    # TODO: FIXME: Add current user to log
    # TODO: FIXME: Make log in background_task
    # TODO: FIXME: Replace all '{something}id' to 'id'
    # TODO: FIXME: Move models folder to a local pip package
    class Meta:
        abstract = True

    @classmethod
    def log_action(cls, message, graphql_info):
        op = str(graphql_info.operation)
        current_user = cls.get_current_user()
        if current_user:
            user_email = current_user.email
        else:
            user_email = 'unknown'
        log = ActionsLogModel(
            user=user_email, context=op, action=message, origin="GraphQL API"
        )
        log.save()

    @classmethod
    def get_current_user(cls):
        # Returns the currently logged user
        # TODO: FIXME: For now, we return the same user for all requests
        return UserModel.objects(email="seed@dacot.uoct.cl").first()

    @classmethod
    def get_b64file_data(cls, base64data):
        _, filedata = base64data.split(",")
        b64bytes = base64.b64decode(filedata)
        mime = magic.from_buffer(b64bytes[0:2048], mime=True)
        return b64bytes, mime


class QueryRootUtils:
    def log_action(self, message, graphql_info):
        op = str(graphql_info.operation)
        current_user = self.get_current_user()
        if current_user:
            user_email = current_user.email
        else:
            user_email = 'unknown'
        log = ActionsLogModel(
            user=user_email, context=op, action=message, origin="GraphQL API"
        )
        log.save()

    def get_current_user(self):
        # Returns the currently logged user
        # TODO: FIXME: For now, we return the same user for all requests
        return UserModel.objects(email="seed@dacot.uoct.cl").first()


RANGE_SCALAR_MAX_VALUE = 50


class RangeScalar(graphene.Int):
    def __init__(self, required=False):
        super().__init__(required)

    @staticmethod
    def coerce_int(value):
        num = graphene.Int.coerce_int(value)
        if num > RANGE_SCALAR_MAX_VALUE:
            raise ValueError('Value {} is greater than max {}'.format(num, RANGE_SCALAR_MAX_VALUE))
        return num

    @staticmethod
    def parse_literal(ast):
        num = graphene.Int.parse_literal(ast)
        if num > RANGE_SCALAR_MAX_VALUE:
            raise ValueError('Value {} is greater than max {}'.format(num, RANGE_SCALAR_MAX_VALUE))
        return num


class Query(graphene.ObjectType):
    users = graphene.List(User)
    user = graphene.Field(User, email=graphene.NonNull(graphene.String))
    actions_logs = graphene.List(ActionsLog)  # TODO: Add pagination
    actions_log = graphene.Field(ActionsLog, logid=graphene.NonNull(graphene.String))
    communes = graphene.List(Commune)
    companies = graphene.List(ExternalCompany)
    failed_plans = graphene.List(PartialPlanParseFailedMessage)  # TODO: Add pagination
    failed_plan = graphene.Field(PlanParseFailedMessage, mid=graphene.NonNull(graphene.String))
    controller_models = graphene.List(ControllerModel)
    # otus = graphene.List(OTU) # Disabled for performance
    otu = graphene.Field(OTU, oid=graphene.NonNull(graphene.String))
    # junctions = graphene.List(Junction) # Disabled for performance
    junction = graphene.Field(Junction, jid=graphene.NonNull(graphene.String))
    # all_projects = graphene.List(Project) # Disabled for performance
    projects = MongoengineConnectionField(Project,
                                          metadata__status=graphene.NonNull(graphene.String),
                                          metadata__version=graphene.NonNull(graphene.String),
                                          first=RangeScalar(required=True))
    project = graphene.Field(
        Project,
        oid=graphene.NonNull(graphene.String),
        status=graphene.NonNull(graphene.String),
    )
    versions = graphene.List(PartialVersionInfo, oid=graphene.NonNull(graphene.String))
    version = graphene.Field(
        Project,
        oid=graphene.NonNull(graphene.String),
        vid=graphene.NonNull(graphene.String),
    )
    login_api_key = graphene.String(
        key=graphene.NonNull(graphene.String), secret=graphene.NonNull(graphene.String)
    )
    check_otu_exists = graphene.Boolean(oid=graphene.NonNull(graphene.String))
    # $ full_schema_drop = graphene.Boolean() # Disabled in production
    compute_tables = graphene.Boolean(jid=graphene.NonNull(graphene.String), status=graphene.NonNull(graphene.String))

    def __compute_plan_table(junc):
        max_phid = -1
        isys = {}
        for plan in junc.plans:
            plid = plan.plid
            isys[plid] = {}
            for sys in plan.system_start:
                isys[plid][sys.phid] = sys.value
                if sys.phid > max_phid:
                    max_phid = sys.phid
        # $ logger.warning(isys)
        eps = {}
        for intg in junc.intergreens:
            intgfrom = ord(intg.phfrom) - 64
            intgto = ord(intg.phto) - 64
            if intgfrom not in eps:
                eps[intgfrom] = {}
            eps[intgfrom][intgto] = int(intg.value)
        # $ logger.warning(eps)
        evs = {}
        for intg in junc.veh_intergreens:
            intgfrom = ord(intg.phfrom) - 64
            intgto = ord(intg.phto) - 64
            if intgfrom not in evs:
                evs[intgfrom] = {}
            evs[intgfrom][intgto] = int(intg.value)
        # $ logger.warning(evs)
        temp_res = {}
        for plan in junc.plans:
            plid = plan.plid
            temp_res[plid] = {}
            for phid, ph_isys in isys[plid].items():
                if phid - 1 in eps:
                    pheps = eps[phid - 1][phid]
                    phevs = evs[phid - 1][phid]
                else:
                    pheps = eps[max_phid][1]
                    phevs = evs[max_phid][1]
                ifs = ph_isys + pheps - phevs
                alpha = int(ifs > plan.cycle)
                ifs = ifs - alpha * plan.cycle
                iv = ifs + phevs
                beta = int(iv > plan.cycle)
                iv = iv - beta * plan.cycle
                row = (plid, plan.cycle, ifs, phevs, iv, pheps, ph_isys)
                temp_res[plid][phid] = row
                # $ logger.warning('F{} => {}'.format(phid, row))
        final_result = {}
        for plid, phases in temp_res.items():
            final_result[plid] = {}
            for phid, row in phases.items():
                if phid + 1 in phases:
                    phid_next = phid + 1
                else:
                    phid_next = 1
                tvv = phases[phid_next][2] - row[4]
                gamma = int(tvv < 0)
                tvv = tvv + gamma * row[1]
                tvp = phases[phid_next][2] - row[4] - (phases[phid_next][5] - phases[phid_next][3])
                delta = int(tvp < 0)
                tvp = tvp + delta * row[1]
                new_row = (row[0], row[1], row[2], row[3], row[4], tvv, tvp, row[5], row[6])
                final_result[plid][phid] = new_row
                # $ logger.warning('{} | F{} => TVV={} TVP={}'.format(plid, phid, tvv, tvp))
        return final_result

    def __save_computed_plan_table(junc, table):
        new_plans = []
        veh_inters = []
        ped_inters = []
        for inter in junc.intergreens:
            inter_i = JunctionPlanIntergreenValueModel()
            inter_i.value = int(inter.value)
            inter_i.phfrom = ord(inter.phfrom) - 64
            inter_i.phto = ord(inter.phto) - 64
            ped_inters.append(inter_i)
        for inter in junc.veh_intergreens:
            inter_i = JunctionPlanIntergreenValueModel()
            inter_i.value = int(inter.value)
            inter_i.phfrom = ord(inter.phfrom) - 64
            inter_i.phto = ord(inter.phto) - 64
            veh_inters.append(inter_i)
        for plan in junc.plans:
            starts = []
            green_starts = []
            veh_greens = []
            ped_greens = []
            for phid, row in table[plan.plid].items():
                start_i = JunctionPlanPhaseValueModel()
                start_i.phid = phid
                start_i.value = row[2]
                starts.append(start_i)
                green_st_i = JunctionPlanPhaseValueModel()
                green_st_i.phid = phid
                green_st_i.value = row[4]
                green_starts.append(green_st_i)
                veh_g_i = JunctionPlanPhaseValueModel()
                veh_g_i.phid = phid
                veh_g_i.value = row[5]
                veh_greens.append(veh_g_i)
                ped_g_i = JunctionPlanPhaseValueModel()
                ped_g_i.phid = phid
                ped_g_i.value = row[6]
                ped_greens.append(ped_g_i)
            plan.phase_start = starts
            plan.green_start = green_starts
            plan.vehicle_green = veh_greens
            plan.pedestrian_green = ped_greens
            plan.vehicle_intergreen = veh_inters
            plan.pedestrian_intergreen = ped_inters
            new_plans.append(plan)
        junc.plans = new_plans
        return junc

    def resolve_compute_tables(self, info, jid, status):
        try:
            oid = 'X{}0'.format(jid[1:-1])
            proj = ProjectModel.objects(
                oid=oid, metadata__status=status, metadata__version="latest"
            ).first()
            if not proj:
                return False
            new_juncs = []
            found = False
            for junc in proj.otu.junctions:
                if junc.jid == jid:
                    table = Query.__compute_plan_table(junc)
                    junc = Query.__save_computed_plan_table(junc, table)
                    found = True
                new_juncs.append(junc)
            if not found:
                return found
            proj.otu.junctions = new_juncs
            proj.save()
            return found
        except Exception as excp:
            return GraphQLError(str(excp))

    def resolve_full_schema_drop(self, info):
        logger.warning('FullSchemaDrop Requested')
        PlanParseFailedMessageModel.drop_collection()
        ProjectModel.drop_collection()
        ActionsLogModel.drop_collection()
        ControllerModelModel.drop_collection()
        CommuneModel.drop_collection()
        UserModel.drop_collection()
        ExternalCompanyModel.drop_collection()
        logger.warning('FullSchemaDrop Done')
        return True

    def resolve_check_otu_exists(self, info, oid):
        proj = ProjectModel.objects(oid=oid).only("id").first()
        return proj != None

    def resolve_all_projects(self, info):
        return ProjectModel.objects.all()

    def resolve_login_api_key(self, info, key, secret):
        authorize = info.context["request"].state.authorize
        utils = QueryRootUtils()
        user = APIKeyUsersModel.objects(key=key, secret=secret).first()
        if user:
            token = authorize.create_access_token(subject=key)
            utils.log_action('APIKeyUser {} logged in'.format(key), info)
            return token
        else:
            utils.log_action('Invalid credentials for APIKeyUser {}'.format(key), info)
            return GraphQLError('Invalid credentials for APIKeyUser {}'.format(key))

    def resolve_version(self, info, oid, vid):
        version = (
            ProjectModel.objects(
                oid=oid, metadata__status="PRODUCTION", metadata__version=vid
            )
                .exclude("metadata.pdf_data")
                .first()
        )
        if not version:
            return GraphQLError('Version "{}" not found'.format(vid))
        return version

    def resolve_versions(self, info, oid):
        result = []
        project_versions = (
            ProjectModel.objects(oid=oid, metadata__status="PRODUCTION")
                .order_by("-status_date")
                .only("metadata.version", "metadata.status_date", "observation")
                .all()
        )
        for ver in project_versions:
            vinfo = PartialVersionInfo()
            vinfo.vid = ver.metadata.version
            vinfo.date = ver.metadata.status_date
            vinfo.comment = ver.observation
            result.append(vinfo)
        return result

    def resolve_project(self, info, oid, status):
        return ProjectModel.objects(
            oid=oid, metadata__status=status, metadata__version="latest"
        ).first()

    def resolve_junctions(self, info):
        juncs = []
        projects = ProjectModel.objects.only("otu.junctions").all()
        for proj in projects:
            juncs.extend(proj.otu.junctions)
        return juncs

    def resolve_junction(self, info, jid):
        proj = (
            ProjectModel.objects(otu__junctions__jid=jid).only("otu.junctions").first()
        )
        if proj:
            for junc in proj.junctions:
                if junc.jid == jid:
                    return junc
        return None

    def resolve_otus(self, info):
        projects = ProjectModel.objects.only("otu").all()
        return [proj.otu for proj in projects]

    def resolve_otu(self, info, oid):
        proj = ProjectModel.objects(oid=oid).only("otu").first()
        if proj:
            return proj.otu
        return None

    def resolve_controller_models(self, info):
        return list(ControllerModelModel.objects.all())

    def resolve_failed_plans(self, info):
        return list(
            PlanParseFailedMessageModel.objects.only("id", "date", "comment").all()
        )

    def resolve_failed_plan(self, info, mid):
        return PlanParseFailedMessageModel.objects(id=mid).first()

    def resolve_companies(self, info):
        return list(ExternalCompanyModel.objects.all())

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


class ControllerModelInput(graphene.InputObjectType):
    company = graphene.NonNull(graphene.String)
    model = graphene.NonNull(graphene.String)
    firmware_version = graphene.NonNull(graphene.String)
    checksum = graphene.NonNull(graphene.String)


class ControllerLocationInput(graphene.InputObjectType):
    address_reference = graphene.String()
    gps = graphene.Boolean()
    model = graphene.NonNull(ControllerModelInput)


class ProjectHeadersInput(graphene.InputObjectType):
    hal = graphene.NonNull(graphene.Int)
    led = graphene.NonNull(graphene.Int)
    type = graphene.NonNull(graphene.String)


class ProjectUPSInput(graphene.InputObjectType):
    brand = graphene.NonNull(graphene.String)
    model = graphene.NonNull(graphene.String)
    serial = graphene.NonNull(graphene.String)
    capacity = graphene.NonNull(graphene.String)
    charge_duration = graphene.NonNull(graphene.String)


class ProjectPolesInput(graphene.InputObjectType):
    hooks = graphene.NonNull(graphene.Int)
    vehicular = graphene.NonNull(graphene.Int)
    pedestrian = graphene.NonNull(graphene.Int)


class ProjectMetaInput(graphene.InputObjectType):
    installation_date = graphene.Date()
    installation_company = graphene.String()
    maintainer = graphene.NonNull(graphene.String)
    commune = graphene.NonNull(graphene.Int)
    # img = graphene.Base64()
    # pdf_data = graphene.Base64()
    pedestrian_demand = graphene.Boolean()
    pedestrian_facility = graphene.Boolean()
    local_detector = graphene.Boolean()
    scoot_detector = graphene.Boolean()


class OTUMetadataInput(graphene.InputObjectType):
    serial = graphene.String()
    ip_address = graphene.String()
    netmask = graphene.String()
    control = graphene.Int()
    answer = graphene.Int()
    link_type = graphene.String()
    link_owner = graphene.String()


class OTUProgramInput(graphene.InputObjectType):
    day = graphene.NonNull(graphene.String)
    time = graphene.NonNull(graphene.String)
    plan = graphene.NonNull(graphene.String)


class JunctionPhasesSequenceInput(graphene.InputObjectType):
    phid = graphene.NonNull(graphene.String)
    phid_system = graphene.NonNull(graphene.String)
    type = graphene.NonNull(graphene.String)


class JunctionMetadataInput(graphene.InputObjectType):
    coordinates = graphene.NonNull(graphene.List(graphene.NonNull(graphene.Float)))
    address_reference = graphene.NonNull(graphene.String)


class JunctionPlanPhaseValueInput(graphene.InputObjectType):
    phid = graphene.NonNull(graphene.Int)
    value = graphene.NonNull(graphene.Int)


class JunctionPlanInput(graphene.InputObjectType):
    plid = graphene.NonNull(graphene.Int)
    cycle = graphene.NonNull(graphene.Int)
    system_start = graphene.NonNull(graphene.List(graphene.NonNull(JunctionPlanPhaseValueInput)))


class JunctionIntergreenValueInput(graphene.InputObjectType):
    phfrom = graphene.NonNull(graphene.String)
    phto = graphene.NonNull(graphene.String)
    value = graphene.NonNull(graphene.String)


class ProjectJunctionInput(graphene.InputObjectType):
    jid = graphene.NonNull(graphene.String)
    metadata = graphene.NonNull(JunctionMetadataInput)
    sequence = graphene.List(JunctionPhasesSequenceInput)
    plans = graphene.List(JunctionPlanInput)
    intergreens = graphene.List(JunctionIntergreenValueInput)


class ProjectOTUInput(graphene.InputObjectType):
    metadata = OTUMetadataInput()
    junctions = graphene.NonNull(graphene.List(graphene.NonNull(ProjectJunctionInput)))
    program = graphene.List(OTUProgramInput)


class CreateProjectInput(graphene.InputObjectType):
    oid = graphene.NonNull(graphene.String)
    metadata = graphene.NonNull(ProjectMetaInput)
    otu = graphene.NonNull(ProjectOTUInput)
    controller = graphene.NonNull(ControllerLocationInput)
    headers = graphene.List(ProjectHeadersInput)
    ups = ProjectUPSInput()
    poles = ProjectPolesInput()
    observation = graphene.NonNull(graphene.String)


class DeleteControllerModelInput(graphene.InputObjectType):
    cid = graphene.NonNull(graphene.String)


# class SetVehicleIntergreenItemInput(graphene.InputObjectType):
#    phid = graphene.NonNull(graphene.String)
#    value = graphene.NonNull(graphene.Int)

class SetVehicleIntergreenInput(graphene.InputObjectType):
    jid = graphene.NonNull(graphene.String)
    status = graphene.NonNull(graphene.String)
    phases = graphene.List(graphene.NonNull(JunctionIntergreenValueInput))


# class DeleteController(CustomMutation):
#    pass

class SetDefaultVehicleIntergreen(CustomMutation):
    class Arguments:
        data = SetVehicleIntergreenInput()

    Output = graphene.String

    @classmethod
    def update_model_default(cls, data, info, proj, junc):
        veh_inters = []
        for ped_inter in junc.intergreens:
            new_inter = JunctionIntergreenValueModel()
            new_inter.phfrom = ped_inter.phfrom
            new_inter.phto = ped_inter.phto
            new_inter.value = 4
            veh_inters.append(new_inter)
        junc.veh_intergreens = veh_inters
        try:
            proj.save()
        except ValidationError as excep:
            msg = 'Failed to save project. Cause: {}'.format(str(excep))
            cls.log_action(msg, info)
            return GraphQLError(msg)
        return data.jid

    @classmethod
    def update_model_custom(cls, data, info, proj, junc):
        logger.warning(data)
        input_inters_from = {}
        input_inters_to = {}
        for phase in data.phases:
            input_inters_from[phase['phfrom']] = None
            input_inters_to[phase['phto']] = None
        a = len(input_inters_from)
        b = len(input_inters_to)
        needed = len(junc.intergreens)
        logger.warning((a, b, needed))
        if a != b or a != needed:
            msg = 'Failed to set VI values, number of phases in input mismatch. Needed {}, got {} (from) and {} (to)'.format(needed, a, b)
            cls.log_action(msg, info)
            return GraphQLError(msg)
        logger.warning(input_inters_from)
        for ped_inter in junc.intergreens:
            new_inter = JunctionIntergreenValueModel()
            new_inter.phfrom = ped_inter.phfrom
            new_inter.phto = ped_inter.phto
            new_inter.value = -5
            logger.warning(new_inter.to_mongo())
        logger.warning('On update_model_custom')
        return data.jid

    @classmethod
    def set_vi(cls, data, info, is_default=True):
        oid = 'X{}0'.format(data.jid[1:-1])
        proj = ProjectModel.objects(oid=oid, metadata__status=data.status).first()
        if not proj:
            msg = 'Failed to find project "{}" in status "{}". Project not found'.format(oid, data.status)
            cls.log_action(msg, info)
            return GraphQLError(msg)
        for junc in proj.otu.junctions:
            if junc.jid == data.jid:
                if is_default:
                    return cls.update_model_default(data, info, proj, junc)
                else:
                    return cls.update_model_custom(data, info, proj, junc)
        msg = 'Failed to find junction "{}" in project "{}". Junction not found'.format(data.jid, oid)
        cls.log_action(msg, info)
        return GraphQLError(msg)

    @classmethod
    def mutate(cls, root, info, data):
        return cls.set_vi(data, info)


class SetIntergreen(SetDefaultVehicleIntergreen):
    class Arguments:
        data = SetVehicleIntergreenInput()

    Output = graphene.String

    @classmethod
    def mutate(cls, root, info, data):
        return cls.set_vi(data, info, is_default=False)


class CreateProject(CustomMutation):
    class Arguments:
        project_details = CreateProjectInput()

    Output = Project

    @classmethod
    def build_metadata_files(cls, meta, metain, oid, info):
        if metain.img:
            fdata, ftype = cls.get_b64file_data(metain.img)
            if ftype in ["image/jpeg", "image/png"]:
                meta.img.put(fdata, content_type=ftype)
            else:
                cls.log_action(
                    'Failed to create project "{}". Invalid image file type: "{}"'.format(
                        oid, ftype
                    ),
                    info,
                )
                return GraphQLError('Invalid image file type: "{}"'.format(ftype))
        if metain.pdf_data:
            fdata, ftype = cls.get_b64file_data(metain.pdf_data)
            if ftype in ["application/pdf"]:
                meta.pdf_data.put(fdata, content_type=ftype)
            else:
                cls.log_action(
                    'Failed to create project "{}". Invalid  file type: "{}"'.format(
                        oid, ftype
                    ),
                    info,
                )
                return GraphQLError(
                    'Invalid PDF document file type: "{}"'.format(ftype)
                )
        return meta

    @classmethod
    def build_metadata_options(cls, meta, metain):
        if metain.pedestrian_demand:
            meta.pedestrian_demand = metain.pedestrian_demand
        if metain.pedestrian_facility:
            meta.pedestrian_facility = metain.pedestrian_facility
        if metain.local_detector:
            meta.local_detector = metain.local_detector
        if metain.scoot_detector:
            meta.scoot_detector = metain.scoot_detector
        return meta

    @classmethod
    def build_metadata(cls, metain, oid, info):
        meta = ProjectMetaModel()
        meta.status = "NEW"
        meta.status_user = cls.get_current_user()
        if metain.installation_date:
            meta.installation_date = metain.installation_date
        if metain.installation_company:
            installation_company = ExternalCompanyModel.objects(
                name=metain.installation_company
            ).first()
            if not installation_company:
                cls.log_action(
                    'Failed to create project "{}". Company "{}" not found'.format(
                        oid, metain.installation_company
                    ),
                    info,
                )
                return GraphQLError(
                    'Company "{}" not found'.format(metain.installation_company)
                )
            meta.installation_company = installation_company
        maintainer = ExternalCompanyModel.objects(name=metain.maintainer).first()
        if not maintainer:
            cls.log_action(
                'Failed to create project "{}". Company "{}" not found'.format(
                    oid, metain.maintainer
                ),
                info,
            )
            return GraphQLError('Company "{}" not found'.format(metain.maintainer))
        meta.maintainer = maintainer
        commune = CommuneModel.objects(code=metain.commune).first()
        if not commune:
            cls.log_action(
                'Failed to create project "{}". Commune "{}" not found'.format(
                    oid, metain.commune
                ),
                info,
            )
            return GraphQLError('Commune "{}" not found'.format(metain.commune))
        meta.commune = commune
        meta = cls.build_metadata_options(meta, metain)
        return cls.build_metadata_files(meta, metain, oid, info)

    @classmethod
    def build_otu_meta(cls, metain, oid, info):
        meta = OTUMetaModel()
        if metain.serial:
            meta.serial = metain.serial
        if metain.ip_address:
            meta.ip_address = metain.ip_address
        if metain.netmask:
            meta.netmask = metain.netmask
        if metain.control:
            meta.control = metain.control
        if metain.answer:
            meta.answer = metain.answer
        if metain.link_type:
            meta.link_type = metain.link_type
        if metain.link_owner:
            meta.link_owner = metain.link_owner
        return meta

    @classmethod
    def build_otu(cls, otuin, oid, info):
        otu = OTUModel()
        otu.oid = oid
        if otuin.metadata:
            otu.meta = cls.build_otu_meta(otuin, oid, info)
        junctions = []
        for junc in otuin.junctions:
            otu_junc = JunctionModel()
            otu_junc.jid = junc.jid
            junc_meta = JunctionMetaModel()
            junc_meta.sales_id = round((int(junc.jid[1:]) * 11) / 13.0)
            junc_meta.address_reference = junc.metadata.address_reference
            junc_meta.location = (
                junc.metadata.coordinates[0],
                junc.metadata.coordinates[1],
            )
            otu_junc.metadata = junc_meta
            if junc.sequence:
                junc_seqs = []
                for seq in junc.sequence:
                    db_seq = JunctionPhaseSequenceItemModel()
                    db_seq.phid = seq.phid
                    db_seq.phid_system = seq.phid_system
                    db_seq.type = seq.type
                    junc_seqs.append(db_seq)
                otu_junc.sequence = junc_seqs
            if junc.plans:
                junc_plans = []
                for plan in junc.plans:
                    db_plan = JunctionPlanModel()
                    db_plan.plid = plan.plid
                    db_plan.cycle = plan.cycle
                    system_starts = []
                    for start in plan.system_start:
                        new_start = JunctionPlanPhaseValueModel()
                        new_start.phid = start.phid
                        new_start.value = start.value
                        system_starts.append(new_start)
                    db_plan.system_start = system_starts
                    junc_plans.append(db_plan)
                otu_junc.plans = junc_plans
            if junc.intergreens:
                junc_inters = []
                for inter in junc.intergreens:
                    new_inter = JunctionIntergreenValueModel()
                    new_inter.phfrom = inter.phf
                    new_inter.phto = inter.pht
                    new_inter.value = inter.val
                    junc_inters.append(new_inter)
                otu_junc.intergreens = junc_inters
            junctions.append(otu_junc)
        if otuin.program:
            db_progs = []
            for prog in otuin.program:
                new_prog = OTUProgramItemModel()
                new_prog.day = prog.day
                new_prog.time = prog.time
                new_prog.plan = prog.plan
                db_progs.append(new_prog)
            otu.programs = db_progs
        otu.junctions = junctions
        return otu

    @classmethod
    def build_controller_info(cls, controller_in, oid, info):
        ctrl = ProjControllerModel()
        if controller_in.address_reference:
            ctrl.address_reference = controller_in.address_reference
        if controller_in.gps:
            ctrl.gps = controller_in.gps
        company = ExternalCompanyModel.objects(name=controller_in.model.company).first()
        if not company:
            cls.log_action(
                'Failed to create project "{}". Company "{}" not found'.format(
                    oid, controller_in.model.company
                ),
                info,
            )
            return GraphQLError(
                'Company "{}" not found'.format(controller_in.model.company)
            )
        model = ControllerModelModel.objects(
            company=company,
            model=controller_in.model.model,
            firmware_version=controller_in.model.firmware_version,
            checksum=controller_in.model.checksum,
        ).first()
        if not model:
            cls.log_action(
                'Failed to create project "{}". Model "{}" not found'.format(
                    oid, controller_in.model
                ),
                info,
            )
            return GraphQLError('Model "{}" not found'.format(controller_in.model))
        ctrl.model = model
        return ctrl

    @classmethod
    def build_project_model(cls, project_details, info):
        proj = ProjectModel()
        proj.oid = project_details.oid
        # Metadata
        meta_result = cls.build_metadata(
            project_details.metadata, project_details.oid, info
        )
        if isinstance(meta_result, GraphQLError):
            cls.log_action(
                'Failed to create project "{}". {}'.format(proj.oid, meta_result), info
            )
            return meta_result
        proj.metadata = meta_result
        # OTU
        for junc in project_details.otu.junctions:
            coordlen = len(junc.metadata.coordinates)
            if coordlen != 2:
                cls.log_action(
                    'Failed to create project "{}". Invalid length for coordinates in jid "{}": {}'.format(
                        project_details.oid, junc.jid, coordlen
                    ),
                    info,
                )
                GraphQLError(
                    'Invalid length for coordinates in jid "{}": {}'.format(
                        junc.jid, coordlen
                    )
                )
        proj.otu = cls.build_otu(project_details.otu, project_details.oid, info)
        # Controller info
        ctrl_result = cls.build_controller_info(
            project_details.controller, project_details.oid, info
        )
        if isinstance(ctrl_result, GraphQLError):
            cls.log_action(
                'Failed to create project "{}". {}'.format(proj.oid, ctrl_result), info
            )
            return ctrl_result
        proj.controller = ctrl_result
        # Headers
        if project_details.headers:
            headers = []
            for head in project_details.headers:
                header_item = ProjectHeaderItemModel()
                header_item.hal = head.hal
                header_item.led = head.led
                header_item.type = head.type
                headers.append(header_item)
            proj.headers = headers
        # UPS
        if project_details.ups:
            ups = UPSModel()
            ups.brand = project_details.ups.brand
            ups.model = project_details.ups.model
            ups.serial = project_details.ups.serial
            ups.capacity = project_details.ups.capacity
            ups.charge_duration = project_details.ups.charge_duration
            proj.ups = ups
        # Poles
        if project_details.poles:
            poles = PolesModel()
            poles.hooks = project_details.poles.hooks
            poles.vehicular = project_details.poles.vehicular
            poles.pedestrian = project_details.poles.pedestrian
            proj.poles = poles
        # Observations
        obs = CommentModel()
        obs.author = cls.get_current_user()
        obs.message = project_details.observation
        proj.observation = obs
        return proj

    @classmethod
    def mutate(cls, root, info, project_details):
        proj = cls.build_project_model(project_details, info)
        if isinstance(proj, GraphQLError):
            return proj
        # Save
        try:
            # TODO: FIXME: Before we save a new project, check if an update exists with the same oid
            proj.save()
        except ValidationError as excep:
            cls.log_action(
                'Failed to create project "{}". {}'.format(proj.oid, excep), info
            )
            return GraphQLError(str(excep))
        cls.log_action('Project "{}" created.'.format(proj.oid), info)
        # TODO: Send notification emails
        return proj


class UpdateProject(CreateProject):
    class Arguments:
        project_details = CreateProjectInput()

    Output = Project

    @classmethod
    def mutate(cls, root, info, project_details):
        update_input = cls.build_project_model(project_details, info)
        if isinstance(update_input, GraphQLError):
            return update_input
        update_input.metadata.status = "UPDATE"
        try:
            update_input.save()
        except ValidationError as excep:
            cls.log_action(
                'Failed to create update for project "{}". {}'.format(
                    update_input.oid, excep
                ),
                info,
            )
            return GraphQLError(str(excep))
        return update_input


class GetProjectInput(graphene.InputObjectType):
    oid = graphene.NonNull(graphene.String)
    status = graphene.NonNull(graphene.String)


class DeleteProject(CustomMutation):
    class Arguments:
        project_details = GetProjectInput()

    Output = graphene.String

    @classmethod
    def mutate(cls, root, info, project_details):
        if project_details == "PRODUCTION":
            cls.log_action(
                'Failed to delete project "{}". Cannot delete data in PRODUCTION status'.format(
                    project_details.oid
                ),
                info,
            )
            return GraphQLError(
                'Failed to delete project "{}". Cannot delete data in PRODUCTION status'.format(
                    project_details.oid
                )
            )
        proj = ProjectModel.objects(
            oid=project_details.oid, metadata__status=project_details.status
        ).first()
        if not proj:
            cls.log_action(
                'Failed to delete project "{}" in status "{}". Project not found'.format(
                    project_details.oid, project_details.status
                ),
                info,
            )
            return GraphQLError(
                'Project "{}" in status "{}" not found'.format(
                    project_details.oid, project_details.status
                )
            )
        try:
            proj.delete()
        except ValidationError as excep:
            cls.log_action(
                'Failed to delete project "{}" in status "{}": {}'.format(
                    project_details.oid, project_details.status, excep
                ),
                info,
            )
            return GraphQLError(str(excep))
        return project_details.oid


class AcceptProject(CustomMutation):
    class Arguments:
        project_details = GetProjectInput()

    Output = graphene.String

    @classmethod
    def mutate(cls, root, info, project_details):
        if project_details.status not in ["NEW", "UPDATE"]:
            cls.log_action(
                'Failed to accept project "{}". Invalid status: {}'.format(
                    project_details.oid, project_details.status
                ),
                info,
            )
            return GraphQLError("Invalid status: {}".format(project_details.status))
        proj = ProjectModel.objects(
            oid=project_details.oid,
            metadata__status=project_details.status,
            metadata__version="latest",
        ).first()
        if not proj:
            cls.log_action(
                'Failed to accept project "{}" in status "{}". Project not found'.format(
                    project_details.oid, project_details.status
                ),
                info,
            )
            return GraphQLError(
                'Project "{}" in status "{}" not found'.format(
                    project_details.oid, project_details.status
                )
            )
        if project_details.status == "UPDATE":
            # Find latest version
            base_proj = ProjectModel.objects(
                oid=project_details.oid,
                metadata__status="PRODUCTION",
                metadata__version="latest",
            ).first()
            if not base_proj:
                cls.log_action(
                    'Failed to update project "{}". Base version not found'.format(
                        project_details.oid
                    ),
                    info,
                )
                return GraphQLError("Base version not found")
            # Old latest is '$now' version
            new_version = datetime.now().isoformat()
            base_proj.metadata.version = new_version
            # New input will be the latest version
            proj.metadata.status = "PRODUCTION"
            try:
                base_proj.save()
                proj.save()
            except ValidationError as excep:
                cls.log_action(
                    'Failed to accept update for project "{}". {}'.format(
                        project_details.oid, excep
                    ),
                    info,
                )
                return GraphQLError(str(excep))
            cls.log_action(
                'Update for project "{}" ACCEPTED'.format(project_details.oid), info
            )
            return proj.oid
        else:
            proj.metadata.status = "PRODUCTION"
            try:
                proj.save()
            except ValidationError as excep:
                cls.log_action(
                    'Failed to accept new project "{}". {}'.format(
                        project_details.oid, excep
                    ),
                    info,
                )
                return GraphQLError(str(excep))
            cls.log_action(
                'New project "{}" ACCEPTED'.format(project_details.oid), info
            )
            return proj.oid


class RejectProject(CustomMutation):
    class Arguments:
        project_details = GetProjectInput()

    Output = graphene.String

    @classmethod
    def mutate(cls, root, info, project_details):
        if project_details.status not in ["NEW", "UPDATE"]:
            cls.log_action(
                'Failed to reject project "{}". Invalid status: {}'.format(
                    project_details.oid, project_details.status
                ),
                info,
            )
            return GraphQLError("Invalid status: {}".format(project_details.status))
        proj = ProjectModel.objects(
            oid=project_details.oid, metadata__status=project_details.status
        ).first()
        if not proj:
            cls.log_action(
                'Failed to reject project "{}" in status "{}". Project not found'.format(
                    project_details.oid, project_details.status
                ),
                info,
            )
            return GraphQLError(
                'Project "{}" in status "{}" not found'.format(
                    project_details.oid, project_details.status
                )
            )
        proj.metadata.status = "REJECTED"
        new_version = datetime.now().isoformat()
        proj.metadata.version = new_version
        try:
            proj.save()
        except ValidationError as excep:
            cls.log_action(
                'Failed to reject project "{}" in status "{}": {}'.format(
                    project_details.oid, project_details.status, excep
                ),
                info,
            )
            return GraphQLError(str(excep))
        cls.log_action('Project "{}" rejected'.format(project_details.oid), info)
        return project_details.oid


class CreateCommuneInput(graphene.InputObjectType):
    code = graphene.NonNull(graphene.Int)
    name = graphene.NonNull(graphene.String)
    maintainer = graphene.String()
    user_in_charge = graphene.String()


class CreateCommune(CustomMutation):
    class Arguments:
        commune_details = CreateCommuneInput()

    Output = Commune

    @classmethod
    def mutate(cls, root, info, commune_details):
        commune = CommuneModel()
        commune.name = commune_details.name
        commune.code = commune_details.code
        if commune_details.maintainer:
            maintainer = ExternalCompanyModel.objects(
                name=commune_details.maintainer
            ).first()
            if not maintainer:
                cls.log_action(
                    'Failed to create commune "{}". Maintainer "{}" not found'.format(
                        commune_details.code, commune_details.maintainer
                    ),
                    info,
                )
                return GraphQLError(
                    'Maintainer "{}" not found'.format(commune_details.maintainer)
                )
            commune.maintainer = maintainer
        if commune_details.user_in_charge:
            user = UserModel.objects(email=commune_details.user_in_charge).first()
            if not user:
                cls.log_action(
                    'Failed to create commune "{}". User "{}" not found'.format(
                        commune_details.code, commune_details.user_in_charge
                    ),
                    info,
                )
                return GraphQLError(
                    'User "{}" not found'.format(commune_details.user_in_charge)
                )
            commune.user_in_charge = user
        try:
            commune.save()
        except ValidationError as excep:
            cls.log_action(
                'Failed to create commune "{}". {}'.format(commune.name, excep), info
            )
            return GraphQLError(str(excep))
        cls.log_action('Commune "{}" created.'.format(commune.name), info)
        return commune


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
            cls.log_action(
                'Failed to update commune "{}". Commune not found'.format(
                    commune_details.code
                ),
                info,
            )
            return GraphQLError('Commune "{}" not found'.format(commune_details.code))
        if commune_details.maintainer:
            maintainer = ExternalCompanyModel.objects(
                name=commune_details.maintainer
            ).first()
            if not maintainer:
                cls.log_action(
                    'Failed to update commune "{}". Maintainer "{}" not found'.format(
                        commune_details.code, commune_details.maintainer
                    ),
                    info,
                )
                return GraphQLError(
                    'Maintainer "{}" not found'.format(commune_details.maintainer)
                )
            commune.maintainer = maintainer
        if commune_details.user_in_charge:
            user = UserModel.objects(email=commune_details.user_in_charge).first()
            if not user:
                cls.log_action(
                    'Failed to update commune "{}". User "{}" not found'.format(
                        commune_details.code, commune_details.user_in_charge
                    ),
                    info,
                )
                return GraphQLError(
                    'User "{}" not found'.format(commune_details.user_in_charge)
                )
            commune.user_in_charge = user
        try:
            commune.save()
        except ValidationError as excep:
            cls.log_action(
                'Failed to update commune "{}". {}'.format(commune.name, excep), info
            )
            return GraphQLError(str(excep))
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
            user.company = ExternalCompanyModel.objects(
                name=user_details.company
            ).first()
            if not user.company:
                cls.log_action(
                    'Failed to create user "{}". ExternalCompany "{}" not found'.format(
                        user.email, user_details.company
                    ),
                    info,
                )
                return GraphQLError(
                    'ExternalCompany "{}" not found'.format(user_details.company)
                )
        try:
            user.save()
        except (ValidationError, NotUniqueError) as excep:
            cls.log_action(
                'Failed to create user "{}". {}'.format(user.email, excep), info
            )
            return GraphQLError(str(excep))
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
            cls.log_action(
                'Failed to delete user "{}". User not found'.format(user_details.email),
                info,
            )
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
            cls.log_action(
                'Failed to update user "{}". User not found'.format(user_details.email),
                info,
            )
            return GraphQLError('User "{}" not found'.format(user_details.email))
        if user_details.is_admin:
            user.is_admin = user_details.is_admin
        if user_details.full_name:
            user.full_name = user_details.full_name
        try:
            user.save()
        except ValidationError as excep:
            cls.log_action(
                'Failed to update user "{}". {}'.format(user_details.email, excep), info
            )
            return GraphQLError(str(excep))
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
            cls.log_action(
                'Failed to create company "{}". {}'.format(company_details.name, excep),
                info,
            )
            return GraphQLError(str(excep))
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
            cls.log_action(
                'Failed to delete company "{}". Company not found'.format(
                    company_details.name
                ),
                info,
            )
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
            cls.log_action(
                'Failed to delete parse failed message "{}". Message not found'.format(
                    message_details.mid
                ),
                info,
            )
            return GraphQLError('Message "{}" not found'.format(message_details.mid))
        mid = message.id
        message.delete()
        cls.log_action('Message "{}" deleted'.format(message_details.mid), info)
        return mid


class CreatePlanParseFailedMessageInput(graphene.InputObjectType):
    plans = graphene.NonNull(graphene.List(graphene.NonNull(graphene.String)))
    message = graphene.NonNull(graphene.String)


class CreatePlanParseFailedMessage(CustomMutation):
    class Arguments:
        message_details = CreatePlanParseFailedMessageInput()

    Output = PlanParseFailedMessage

    @classmethod
    def mutate(cls, root, info, message_details):
        comment = CommentModel()
        comment.message = message_details.message
        comment.author = cls.get_current_user()
        failed_plan = PlanParseFailedMessageModel()
        failed_plan.comment = comment
        failed_plan.plans = message_details.plans
        try:
            failed_plan.save()
        except (ValidationError, NotUniqueError) as excep:
            cls.log_action(
                'Failed to create error message "{}". {}'.format(failed_plan.id, excep),
                info,
            )
            return GraphQLError(str(excep))
        cls.log_action('Error message "{}" created'.format(failed_plan.id), info)
        return failed_plan


class CreateControllerModelInput(graphene.InputObjectType):
    company = graphene.NonNull(graphene.String)
    model = graphene.NonNull(graphene.String)
    firmware_version = graphene.String()
    checksum = graphene.String()


class CreateControllerModel(CustomMutation):
    class Arguments:
        controller_details = CreateControllerModelInput()

    Output = ControllerModel

    @classmethod
    def mutate(cls, root, info, controller_details):
        company = ExternalCompanyModel.objects(name=controller_details.company).first()
        if not company:
            cls.log_action(
                'Failed to create model "{}". Company not found'.format(
                    controller_details.model
                ),
                info,
            )
            return GraphQLError(
                'Company "{}" not found'.format(controller_details.company)
            )
        model = ControllerModelModel()
        model.company = company
        model.model = controller_details.model
        model.firmware_version = controller_details.firmware_version
        model.checksum = controller_details.checksum
        try:
            model.save()
        except (ValidationError, NotUniqueError) as excep:
            cls.log_action(
                'Failed to create model "{}". {}'.format(
                    controller_details.model, excep
                ),
                info,
            )
            return GraphQLError(str(excep))
        cls.log_action('Model "{}" created'.format(controller_details.model), info)
        return model


class UpdateControllerModelInput(graphene.InputObjectType):
    cid = graphene.NonNull(graphene.String)
    firmware_version = graphene.String()
    checksum = graphene.String()


class UpdateControllerModel(CustomMutation):
    class Arguments:
        controller_details = UpdateControllerModelInput()

    Output = ControllerModel

    @classmethod
    def mutate(cls, root, info, controller_details):
        model = ControllerModelModel.objects(id=controller_details.cid).first()
        if not model:
            cls.log_action(
                'Failed to update model "{}". Model not found'.format(
                    controller_details.cid
                ),
                info,
            )
            return GraphQLError('Model "{}" not found'.format(controller_details.cid))
        if controller_details.checksum:
            model.checksum = controller_details.checksum
        if controller_details.firmware_version:
            model.firmware_version = controller_details.firmware_version
        try:
            model.save()
        except ValidationError as excep:
            cls.log_action(
                'Failed to update model "{}". {}'.format(controller_details.cid, excep),
                info,
            )
            return GraphQLError(str(excep))
        cls.log_action('Model "{}" updated.'.format(controller_details.cid), info)
        return model


class Mutation(graphene.ObjectType):
    create_user = CreateUser.Field()
    delete_user = DeleteUser.Field()
    update_user = UpdateUser.Field()
    update_commune = UpdateCommune.Field()
    create_commune = CreateCommune.Field()
    create_company = CreateCompany.Field()
    delete_company = DeleteCompany.Field()
    delete_failed_plan = DeletePlanParseFailedMessage.Field()
    create_failed_plan = CreatePlanParseFailedMessage.Field()
    create_controller = CreateControllerModel.Field()
    update_controller = UpdateControllerModel.Field()
    create_project = CreateProject.Field()
    delete_project = DeleteProject.Field()
    accept_project = AcceptProject.Field()
    reject_project = RejectProject.Field()
    update_project = UpdateProject.Field()
    set_default_intergreen = SetDefaultVehicleIntergreen.Field()
    set_intergreen = SetIntergreen.Field()


dacot_schema = graphene.Schema(query=Query, mutation=Mutation)


class GraphQLLogFilter(logging.Filter):
    def filter(self, record):
        if "graphql.error.located_error.GraphQLLocatedError:" in record.msg:
            return False
        return True


# Disable graphene logging
logging.getLogger("graphql.execution.utils").addFilter(GraphQLLogFilter())
