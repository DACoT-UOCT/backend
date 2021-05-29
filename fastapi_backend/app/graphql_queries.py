import dacot_models as dm
from graphene import *
from graphql_models import *
from fastapi.logger import logger
from graphene_mongo import MongoengineConnectionField as MCF

class Query(ObjectType):
    users = List(User)
    user = Field(User, email=NonNull(String))
    action_log = Field(ActionsLog, logid=NonNull(String))
    action_logs = MCF(ActionsLog)
    communes = List(Commune)
    companies = List(ExternalCompany)
    failed_plans = MCF(PlanParseFailedMessage)
    failed_plan = Field(PlanParseFailedMessage, mid=NonNull(String))
    controllers = List(ControllerModel)
    junction = Field(Junction, jid=NonNull(String), status=NonNull(String))
    projects = MCF(Project, metadata__status=NonNull(String), metadata__version=NonNull(String), first=RangeScalar(required=True))
    locations = List(JunctionLocationItem, status=NonNull(String))
    project = Field(Project, oid=NonNull(String), status=NonNull(String))
    versions = List(PartialVersionInfo, oid=NonNull(String))
    version = Field(Project, oid=NonNull(String), vid=NonNull(String))
    login_api_key = String(key=NonNull(String), secret=NonNull(String))
    check_otu_exists = Boolean(oid=NonNull(String))

    def resolve_users(self, info):
        return dm.User.objects.all()

    def resolve_user(self, info, email):
        return dm.User.objects(email=email).first()

    def resolve_action_log(self, info, logid):
        return dm.ActionsLog.objects(id=logid).first()

    def resolve_communes(self, info):
        return dm.Commune.objects.all()

    def resolve_companies(self, info):
        return dm.ExternalCompany.objects.all()

    def resolve_failed_plan(self, info, mid):
        return dm.PlanParseFailedMessage.objects(id=mid).first()

    def resolve_controllers(self, info):
        return dm.ControllerModel.objects.all()

    def resolve_junction(self, info, jid, status):
        proj = ProjectModel.objects(metadata__status=status, otu__junctions__jid=jid).only('otu.junctions').first()
        if proj:
            for junc in proj.otu.junctions:
                if junc.jid == jid:
                    return junc
        return None

    def resolve_locations(self, info, status):
        projs = dm.Project.objects(metadata__status=status).no_dereference().only('otu.junctions.jid', 'otu.junctions.metadata.location')
        res = []
        for proj in projs:
            for junc in proj.otu.junctions:
                loc = junc.metadata.location['coordinates']
                res.append(JunctionLocationItem(jid=junc.jid, lat=loc[0], lon=loc[1]))
        return res

    def resolve_project(self, info, oid, status):
        return dm.Project.objects(oid=oid, metadata__status=status, metadata__version='latest').first()

    def resolve_versions(self, info, oid):
        result = []
        vers = dm.Project.objects(oid=oid, metadata__status='PRODUCTION').order_by('-status_date').only('metadata.version', 'metadata.status_date', 'observation').all()
        for ver in vers:
            vinfo = PartialVersionInfo()
            vinfo.vid = ver.metadata.version
            vinfo.date = ver.metadata.status_date
            vinfo.comment = ver.observation
            result.append(vinfo)
        return result

    def resolve_version(self, info, oid, vid):
        return dm.Project.objects(oid=oid, metadata__status='PRODUCTION', metadata__version=vid).exclude('metadata.pdf_data').first()

    def resolve_login_api_key(self, info, key, secret):
        authorize = info.context["request"].state.authorize
        user = APIKeyUsersModel.objects(key=key, secret=secret).first()
        if user:
            token = authorize.create_access_token(subject=key)
            return token
        return None

    def resolve_check_otu_exists(self, info, oid):
        return dm.Project.objects(oid=oid, metadata__status='PRODUCTION', metadata__version='latest').first() != None