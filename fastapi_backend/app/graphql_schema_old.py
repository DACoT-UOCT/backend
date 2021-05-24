import base64
import logging
from datetime import datetime

import graphene
import magic
from fastapi.logger import logger
from graphene_mongo import MongoengineObjectType, MongoengineConnectionField
from graphql import GraphQLError
from mongoengine import ValidationError, NotUniqueError

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
    junction = graphene.Field(Junction, jid=graphene.NonNull(graphene.String), status=graphene.NonNull(graphene.String))
    # all_projects = graphene.List(Project) # Disabled for performance
    projects = MongoengineConnectionField(Project,
                                          metadata__status=graphene.NonNull(graphene.String),
                                          metadata__version=graphene.NonNull(graphene.String),
                                          first=RangeScalar(required=True))
    locations = graphene.List(JunctionLocationItem, status=graphene.NonNull(graphene.String))
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
    # TODO: Move compute_tables to a utility class
    compute_tables = graphene.Boolean(jid=graphene.NonNull(graphene.String), status=graphene.NonNull(graphene.String))

    def resolve_locations(self, info, status):
        import datetime
        logger.warning('{}. Starting resolve_locations'.format(datetime.datetime.now().isoformat()))
        all = ProjectModel.objects(metadata__status=status).no_dereference().only('otu.junctions.jid',
                                                                                  'otu.junctions.metadata.location')
        ret = []
        for proj in all:
            for junc in proj.otu.junctions:
                loc = junc.metadata.location['coordinates']
                ret.append(JunctionLocationItem(jid=junc.jid, lat=loc[0], lon=loc[1]))
        logger.warning('{}. Done resolve_locations'.format(datetime.datetime.now().isoformat()))
        return ret

    @staticmethod
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

    @staticmethod
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
        user = APIKeyUsersModel.objects(key=key, secret=secret).first()
        if user:
            token = authorize.create_access_token(subject=key)
            # utils.log_action('APIKeyUser {} logged in'.format(key), info)
            return token
        else:
            # utils.log_action('Invalid credentials for APIKeyUser {}'.format(key), info)
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

    def resolve_junction(self, info, jid, status):
        proj = ProjectModel.objects(metadata__status=status, otu__junctions__jid=jid).only("otu.junctions").first()
        if proj:
            for junc in proj.otu.junctions:
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



class Mutation(graphene.ObjectType):
    update_project = UpdateProject.Field()
