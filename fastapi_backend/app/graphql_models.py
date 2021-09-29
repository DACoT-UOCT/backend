import dacot_models as dm
from graphene_mongo import MongoengineObjectType as MOT, MongoengineConnectionField as MCF
import graphene as gp
from graphene.relay import Node

RANGE_SCALAR_MAX_VALUE = 50

class JunctionIntergreenValue(MOT):
    class Meta:
        model = dm.JunctionIntergreenValue

class JunctionPhaseSequenceItem(MOT):
    class Meta:
        model = dm.JunctionPhaseSequenceItem

class Controller(MOT):
    class Meta:
        model = dm.Controller

class HeaderItem(MOT):
    class Meta:
        model = dm.HeaderItem

class UPS(MOT):
    class Meta:
        model = dm.UPS

class Poles(MOT):
    class Meta:
        model = dm.Poles

class Project(MOT):
    class Meta:
        model = dm.Project
        interfaces = (Node,)

class ProjectMeta(MOT):
    class Meta:
        model = dm.ProjectMeta

class JunctionMeta(MOT):
    class Meta:
        model = dm.JunctionMeta

class JunctionPlan(MOT):
    class Meta:
        model = dm.JunctionPlan

class JunctionPlanPhaseValue(MOT):
    class Meta:
        model = dm.JunctionPlanPhaseValue

class JunctionPlanIntergreenValue(MOT):
    class Meta:
        model = dm.JunctionPlanIntergreenValue

class Junction(MOT):
    class Meta:
        model = dm.Junction

class Comment(MOT):
    class Meta:
        model = dm.Comment

class PlanParseFailedMessage(MOT):
    class Meta:
        model = dm.PlanParseFailedMessage
        interfaces = (Node,)

class SyncFromControlResult(gp.ObjectType):
    oid = gp.NonNull(gp.String)
    code = gp.NonNull(gp.Int)
    date = gp.NonNull(gp.DateTime)
    message = gp.NonNull(gp.String)

class PartialPlanParseFailedMessage(gp.ObjectType):
    id = gp.NonNull(gp.String)
    date = gp.NonNull(gp.DateTime)
    comment = gp.NonNull(Comment)

class ExternalCompany(MOT):
    class Meta:
        model = dm.ExternalCompany

class User(MOT):
    class Meta:
        model = dm.User

class ActionsLog(MOT):
    class Meta:
        model = dm.ActionsLog
        interfaces = (Node,)

class Commune(MOT):
    class Meta:
        model = dm.Commune

class ControllerModel(MOT):
    class Meta:
        model = dm.ControllerModel

class OTU(MOT):
    class Meta:
        model = dm.OTU

class OTUMeta(MOT):
    class Meta:
        model = dm.OTUMeta

class OTUProgramItem(MOT):
    class Meta:
        model = dm.OTUProgramItem

class PartialVersionInfo(gp.ObjectType):
    vid = gp.NonNull(gp.String)
    date = gp.NonNull(gp.DateTime)
    comment = gp.Field(Comment)

class JunctionLocationItem(gp.ObjectType):
    jid = gp.NonNull(gp.String)
    lat = gp.NonNull(gp.Float)
    lon = gp.NonNull(gp.Float)
    commune = gp.NonNull(gp.String)

class RangeScalar(gp.Int):
    def __init__(self, required=False):
        super().__init__(required)

    @staticmethod
    def coerce_int(value):
        num = gp.Int.coerce_int(value)
        if num > RANGE_SCALAR_MAX_VALUE:
            raise ValueError('Value {} is greater than max {}'.format(num, RANGE_SCALAR_MAX_VALUE))
        return num

    @staticmethod
    def parse_literal(ast):
        num = gp.Int.parse_literal(ast)
        if num > RANGE_SCALAR_MAX_VALUE:
            raise ValueError('Value {} is greater than max {}'.format(num, RANGE_SCALAR_MAX_VALUE))
        return num

class ControllerModelInput(gp.InputObjectType):
    company = gp.NonNull(gp.String)
    model = gp.NonNull(gp.String)
    firmware_version = gp.NonNull(gp.String)
    checksum = gp.NonNull(gp.String)

class ControllerLocationInput(gp.InputObjectType):
    address_reference = gp.String()
    gps = gp.Boolean()
    model = gp.NonNull(ControllerModelInput)

class ProjectHeadersInput(gp.InputObjectType):
    hal = gp.NonNull(gp.Int)
    led = gp.NonNull(gp.Int)
    type = gp.NonNull(gp.String)

class ProjectUPSInput(gp.InputObjectType):
    brand = gp.NonNull(gp.String)
    model = gp.NonNull(gp.String)
    serial = gp.NonNull(gp.String)
    capacity = gp.NonNull(gp.String)
    charge_duration = gp.NonNull(gp.String)

class ProjectPolesInput(gp.InputObjectType):
    hooks = gp.NonNull(gp.Int)
    vehicular = gp.NonNull(gp.Int)
    pedestrian = gp.NonNull(gp.Int)

class ProjectMetaInput(gp.InputObjectType):
    installation_date = gp.Date()
    installation_company = gp.String()
    commune = gp.NonNull(gp.Int)
    img = gp.String()
    pdf_data = gp.String()
    pedestrian_demand = gp.Boolean()
    pedestrian_facility = gp.Boolean()
    local_detector = gp.Boolean()
    scoot_detector = gp.Boolean()

class OTUMetadataInput(gp.InputObjectType):
    serial = gp.String()
    ip_address = gp.String()
    netmask = gp.String()
    control = gp.Int()
    answer = gp.Int()
    link_type = gp.String()
    link_owner = gp.String()

class OTUProgramInput(gp.InputObjectType):
    day = gp.NonNull(gp.String)
    time = gp.NonNull(gp.String)
    plan = gp.NonNull(gp.String)

class JunctionPhasesSequenceInput(gp.InputObjectType):
    phid = gp.NonNull(gp.String)
    phid_system = gp.NonNull(gp.String)
    type = gp.NonNull(gp.String)

class JunctionMetadataInput(gp.InputObjectType):
    coordinates = gp.NonNull(gp.List(gp.NonNull(gp.Float)))
    address_reference = gp.NonNull(gp.String)
    use_default_vi4 = gp.Boolean()

class JunctionPlanPhaseValueInput(gp.InputObjectType):
    phid = gp.NonNull(gp.Int)
    value = gp.NonNull(gp.Int)

class JunctionIntergreenValueInput(gp.InputObjectType):
    phfrom = gp.NonNull(gp.String)
    phto = gp.NonNull(gp.String)
    value = gp.NonNull(gp.String)

class JunctionPlanInput(gp.InputObjectType):
    plid = gp.NonNull(gp.Int)
    cycle = gp.NonNull(gp.Int)
    system_start = gp.NonNull(gp.List(gp.NonNull(JunctionPlanPhaseValueInput)))
    green_start = gp.List(gp.NonNull(JunctionPlanPhaseValueInput))
    phase_start = gp.List(gp.NonNull(JunctionPlanPhaseValueInput))
    vehicle_green = gp.List(gp.NonNull(JunctionPlanPhaseValueInput))
    pedestrian_green = gp.List(gp.NonNull(JunctionPlanPhaseValueInput))
    pedestrian_intergreen = gp.List(gp.NonNull(JunctionIntergreenValueInput))
    vehicle_intergreen = gp.List(gp.NonNull(JunctionIntergreenValueInput))

class ProjectJunctionInput(gp.InputObjectType):
    jid = gp.NonNull(gp.String)
    metadata = gp.NonNull(JunctionMetadataInput)
    sequence = gp.List(JunctionPhasesSequenceInput)
    plans = gp.List(JunctionPlanInput)
    intergreens = gp.List(JunctionIntergreenValueInput)
    phases = gp.List(gp.String)    

class ProjectOTUInput(gp.InputObjectType):
    metadata = OTUMetadataInput()
    junctions = gp.NonNull(gp.List(gp.NonNull(ProjectJunctionInput)))
    programs = gp.List(OTUProgramInput)

class CreateProjectInput(gp.InputObjectType):
    oid = gp.NonNull(gp.String)
    metadata = gp.NonNull(ProjectMetaInput)
    status = gp.NonNull(gp.String)
    otu = gp.NonNull(ProjectOTUInput)
    controller = gp.NonNull(ControllerLocationInput)
    headers = gp.List(ProjectHeadersInput)
    ups = ProjectUPSInput()
    poles = ProjectPolesInput()
    observation = gp.NonNull(gp.String)

class SetVehicleIntergreenInput(gp.InputObjectType):
    jid = gp.NonNull(gp.String)
    status = gp.NonNull(gp.String)
    phases = gp.List(gp.NonNull(JunctionIntergreenValueInput))

class GetProjectInput(gp.InputObjectType):
    oid = gp.NonNull(gp.String)
    status = gp.NonNull(gp.String)

class AcceptRejectProjectInput(gp.InputObjectType):
    oid = gp.NonNull(gp.String)
    status = gp.NonNull(gp.String)
    message = gp.String()
    img = gp.String()

class CreateCommuneInput(gp.InputObjectType):
    code = gp.NonNull(gp.Int)
    name = gp.NonNull(gp.String)
    maintainer = gp.String()
    user_in_charge = gp.String()

class UpdateControllerModelInput(gp.InputObjectType):
    cid = gp.NonNull(gp.String)
    firmware_version = gp.String()
    checksum = gp.String()

class CreateControllerModelInput(gp.InputObjectType):
    company = gp.NonNull(gp.String)
    model = gp.NonNull(gp.String)
    firmware_version = gp.String()
    checksum = gp.String()

class CreatePlanParseFailedMessageInput(gp.InputObjectType):
    plans = gp.NonNull(gp.List(gp.NonNull(gp.String)))
    message = gp.NonNull(gp.String)

class DeletePlanParseFailedMessageInput(gp.InputObjectType):
    mid = gp.NonNull(gp.String)

class DeleteCompanyInput(gp.InputObjectType):
    name = gp.NonNull(gp.String)

class CreateCompanyInput(gp.InputObjectType):
    name = gp.NonNull(gp.String)

class CreateUserInput(gp.InputObjectType):
    is_admin = gp.NonNull(gp.Boolean)
    full_name = gp.NonNull(gp.String)
    email = gp.NonNull(gp.String)
    role = gp.NonNull(gp.String)
    area = gp.NonNull(gp.String)
    company = gp.String()

class DeleteUserInput(gp.InputObjectType):
    email = gp.NonNull(gp.String)

class UpdateUserInput(gp.InputObjectType):
    email = gp.NonNull(gp.String)
    is_admin = gp.Boolean()
    full_name = gp.String()

class UpdateCommuneInput(gp.InputObjectType):
    code = gp.NonNull(gp.Int)
    maintainer = gp.String()
    user_in_charge = gp.String()
