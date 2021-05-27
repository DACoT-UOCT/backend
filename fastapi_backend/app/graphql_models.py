import dacot_models as dm
from graphene_mongo import MongoengineObjectType as MOT, MongoengineConnectionField as MCF
from graphene import *
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

class PartialPlanParseFailedMessage(ObjectType):
    id = NonNull(String)
    date = NonNull(DateTime)
    comment = NonNull(Comment)

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

class PartialVersionInfo(ObjectType):
    vid = NonNull(String)
    date = NonNull(DateTime)
    comment = Field(Comment)

class JunctionLocationItem(ObjectType):
    jid = NonNull(String)
    lat = NonNull(Float)
    lon = NonNull(Float)

class RangeScalar(Int):
    def __init__(self, required=False):
        super().__init__(required)

    @staticmethod
    def coerce_int(value):
        num = Int.coerce_int(value)
        if num > RANGE_SCALAR_MAX_VALUE:
            raise ValueError('Value {} is greater than max {}'.format(num, RANGE_SCALAR_MAX_VALUE))
        return num

    @staticmethod
    def parse_literal(ast):
        num = Int.parse_literal(ast)
        if num > RANGE_SCALAR_MAX_VALUE:
            raise ValueError('Value {} is greater than max {}'.format(num, RANGE_SCALAR_MAX_VALUE))
        return num

class ControllerModelInput(InputObjectType):
    company = NonNull(String)
    model = NonNull(String)
    firmware_version = NonNull(String)
    checksum = NonNull(String)

class ControllerLocationInput(InputObjectType):
    address_reference = String()
    gps = Boolean()
    model = NonNull(ControllerModelInput)

class ProjectHeadersInput(InputObjectType):
    hal = NonNull(Int)
    led = NonNull(Int)
    type = NonNull(String)

class ProjectUPSInput(InputObjectType):
    brand = NonNull(String)
    model = NonNull(String)
    serial = NonNull(String)
    capacity = NonNull(String)
    charge_duration = NonNull(String)

class ProjectPolesInput(InputObjectType):
    hooks = NonNull(Int)
    vehicular = NonNull(Int)
    pedestrian = NonNull(Int)

class ProjectMetaInput(InputObjectType):
    installation_date = Date()
    installation_company = String()
    commune = NonNull(Int)
    img = String()
    pdf_data = String()
    pedestrian_demand = Boolean()
    pedestrian_facility = Boolean()
    local_detector = Boolean()
    scoot_detector = Boolean()

class OTUMetadataInput(InputObjectType):
    serial = String()
    ip_address = String()
    netmask = String()
    control = Int()
    answer = Int()
    link_type = String()
    link_owner = String()

class OTUProgramInput(InputObjectType):
    day = NonNull(String)
    time = NonNull(String)
    plan = NonNull(String)

class JunctionPhasesSequenceInput(InputObjectType):
    phid = NonNull(String)
    phid_system = NonNull(String)
    type = NonNull(String)

class JunctionMetadataInput(InputObjectType):
    coordinates = NonNull(List(NonNull(Float)))
    address_reference = NonNull(String)
    use_default_vi4 = Boolean()

class JunctionPlanPhaseValueInput(InputObjectType):
    phid = NonNull(Int)
    value = NonNull(Int)

class JunctionPlanInput(InputObjectType):
    plid = NonNull(Int)
    cycle = NonNull(Int)
    system_start = NonNull(List(NonNull(JunctionPlanPhaseValueInput)))

class JunctionIntergreenValueInput(InputObjectType):
    phfrom = NonNull(String)
    phto = NonNull(String)
    value = NonNull(String)

class ProjectJunctionInput(InputObjectType):
    jid = NonNull(String)
    metadata = NonNull(JunctionMetadataInput)
    sequence = List(JunctionPhasesSequenceInput)
    plans = List(JunctionPlanInput)
    intergreens = List(JunctionIntergreenValueInput)
    phases = List(String)    

class ProjectOTUInput(InputObjectType):
    metadata = OTUMetadataInput()
    junctions = NonNull(List(NonNull(ProjectJunctionInput)))
    program = List(OTUProgramInput)

class CreateProjectInput(InputObjectType):
    oid = NonNull(String)
    metadata = NonNull(ProjectMetaInput)
    otu = NonNull(ProjectOTUInput)
    controller = NonNull(ControllerLocationInput)
    headers = List(ProjectHeadersInput)
    ups = ProjectUPSInput()
    poles = ProjectPolesInput()
    observation = NonNull(String)

class SetVehicleIntergreenInput(InputObjectType):
    jid = NonNull(String)
    status = NonNull(String)
    phases = List(NonNull(JunctionIntergreenValueInput))

class GetProjectInput(InputObjectType):
    oid = NonNull(String)
    status = NonNull(String)

class AcceptRejectProjectInput(InputObjectType):
    oid = NonNull(String)
    status = NonNull(String)
    message = String()
    img = String()

class CreateCommuneInput(InputObjectType):
    code = NonNull(Int)
    name = NonNull(String)
    maintainer = String()
    user_in_charge = String()

class UpdateControllerModelInput(InputObjectType):
    cid = NonNull(String)
    firmware_version = String()
    checksum = String()

class CreateControllerModelInput(InputObjectType):
    company = NonNull(String)
    model = NonNull(String)
    firmware_version = String()
    checksum = String()

class CreatePlanParseFailedMessageInput(InputObjectType):
    plans = NonNull(List(NonNull(String)))
    message = NonNull(String)

class DeletePlanParseFailedMessageInput(InputObjectType):
    mid = NonNull(String)

class DeleteCompanyInput(InputObjectType):
    name = NonNull(String)

class CreateCompanyInput(InputObjectType):
    name = NonNull(String)

class CreateUserInput(InputObjectType):
    is_admin = NonNull(Boolean)
    full_name = NonNull(String)
    email = NonNull(String)
    role = NonNull(String)
    area = NonNull(String)
    company = String()

class DeleteUserInput(InputObjectType):
    email = NonNull(String)

class UpdateUserInput(InputObjectType):
    email = NonNull(String)
    is_admin = Boolean()
    full_name = String()

class UpdateCommuneInput(InputObjectType):
    code = NonNull(Int)
    maintainer = String()
    user_in_charge = String()
