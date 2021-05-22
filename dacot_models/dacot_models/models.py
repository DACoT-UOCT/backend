from datetime import datetime

from mongoengine import BooleanField
from mongoengine import Document, PointField, StringField, ListField, DateTimeField
from mongoengine import EmbeddedDocument, IntField, EmbeddedDocumentListField
from mongoengine import (
    EmbeddedDocumentField,
    EmailField,
    FileField,
    ReferenceField,
)


# TODO: Deletion flags (Cascade, DENY, etc)


class JunctionPlanIntergreenValue(EmbeddedDocument):
    phfrom = IntField(min_value=1, required=True)
    phto = IntField(min_value=1, required=True)
    value = IntField(min_value=0, required=True)


class JunctionIntergreenValue(EmbeddedDocument):
    phfrom = StringField(required=True)
    phto = StringField(required=True)
    value = StringField(required=True)


class JunctionPlanPhaseValue(EmbeddedDocument):
    phid = IntField(min_value=1, required=True)
    value = IntField(min_value=0, required=True)


class JunctionPlan(EmbeddedDocument):
    plid = IntField(min_value=1, required=True)
    cycle = IntField(min_value=1, required=True)
    phase_start = EmbeddedDocumentListField(JunctionPlanPhaseValue)
    vehicle_intergreen = EmbeddedDocumentListField(JunctionPlanIntergreenValue)
    green_start = EmbeddedDocumentListField(JunctionPlanPhaseValue)
    vehicle_green = EmbeddedDocumentListField(JunctionPlanPhaseValue)
    pedestrian_green = EmbeddedDocumentListField(JunctionPlanPhaseValue)
    pedestrian_intergreen = EmbeddedDocumentListField(JunctionPlanIntergreenValue)
    system_start = EmbeddedDocumentListField(JunctionPlanPhaseValue, required=True)


class JunctionMeta(EmbeddedDocument):
    location = PointField(required=True)
    sales_id = IntField(min_value=0, required=True)
    use_default_vi4 = BooleanField(default=True, required=True)
    address_reference = StringField()


class JunctionPhaseSequenceItem(EmbeddedDocument):
    phid = StringField(regex=r"^\d{1,4}!?$", required=True)
    phid_system = StringField(regex=r"^[A-Z]$", required=True)
    type = StringField(choices=["Vehicular", "Peatonal", "Flecha Verde", "Ciclista", "No Configurada"], required=True)


class Junction(EmbeddedDocument):
    jid = StringField(regex=r"J\d{6}", min_length=7, max_length=7, required=True)
    metadata = EmbeddedDocumentField(JunctionMeta, required=True)
    plans = EmbeddedDocumentListField(JunctionPlan)
    sequence = EmbeddedDocumentListField(JunctionPhaseSequenceItem)
    intergreens = EmbeddedDocumentListField(JunctionIntergreenValue)
    veh_intergreens = EmbeddedDocumentListField(JunctionIntergreenValue)
    phases = ListField(StringField())


class ExternalCompany(Document):
    meta = {"collection": "ExternalCompany"}
    name = StringField(min_length=2, required=True, unique=True)


class HeaderItem(EmbeddedDocument):
    hal = IntField(min_value=0)
    led = IntField(min_value=0)
    type = StringField(
        choices=[
            "L1",
            "L2A",
            "L2B",
            "L2C",
            "LD",
            "L3A",
            "L3B",
            "L3C",
            "L4A",
            "L4B",
            "L4C",
            "L5",
            "L6",
            "L7",
            "L8",
            "L9",
            "L10",
        ]
    )


class UPS(EmbeddedDocument):
    brand = StringField()
    model = StringField()
    serial = StringField()
    capacity = StringField()
    charge_duration = StringField()


class Poles(EmbeddedDocument):
    hooks = IntField(min_value=0)
    vehicular = IntField(min_value=0)
    pedestrian = IntField(min_value=0)


class User(Document):
    meta = {"collection": "User"}
    is_admin = BooleanField(default=False)
    full_name = StringField(min_length=5, required=True)
    email = EmailField(required=True, unique=True)
    role = StringField(choices=["Empresa", "Personal UOCT"], required=True)
    area = StringField(
        choices=[
            "Sala de Control",
            "Ingeniería",
            "TIC",
            "Mantenedora",
            "Contratista",
            "Administración",
        ],
        required=True,
    )
    company = ReferenceField(ExternalCompany)


class Commune(Document):
    meta = {"collection": "Commune"}
    code = IntField(min_value=0, required=True, unique=True)
    maintainer = ReferenceField(ExternalCompany)
    user_in_charge = ReferenceField(User)
    name = StringField(unique=True, required=True, min_length=4)


class Comment(EmbeddedDocument):
    date = DateTimeField(default=datetime.utcnow, required=True)
    message = StringField(required=True)
    author = ReferenceField(User, required=True)


class ProjectMeta(EmbeddedDocument):
    version = StringField(required=True, default="latest")
    status = StringField(
        choices=["NEW", "UPDATE", "REJECTED", "APPROVED", "PRODUCTION"], required=True
    )
    status_date = DateTimeField(default=datetime.utcnow, required=True)
    status_user = ReferenceField(User, required=True)
    installation_date = DateTimeField()
    installation_company = ReferenceField(ExternalCompany)
    maintainer = ReferenceField(ExternalCompany)
    commune = ReferenceField(Commune)
    img = FileField()
    pdf_data = FileField()
    pedestrian_demand = BooleanField()
    pedestrian_facility = BooleanField()
    local_detector = BooleanField()
    scoot_detector = BooleanField()


class ControllerModel(Document):
    meta = {"collection": "ControllerModel"}
    company = ReferenceField(
        ExternalCompany,
        required=True,
        unique_with=("model", "firmware_version", "checksum"),
    )
    model = StringField(required=True)
    firmware_version = StringField(required=True, default="Missing Value")
    checksum = StringField(required=True, default="Missing Value")
    date = DateTimeField(default=datetime.utcnow)


class Controller(EmbeddedDocument):
    address_reference = StringField()
    gps = BooleanField()
    model = ReferenceField(ControllerModel)


class OTUProgramItem(EmbeddedDocument):
    day = StringField(choices=["L", "V", "S", "D"], required=True)
    time = StringField(regex=r"\d\d:\d\d", max_length=5, min_length=5, required=True)
    plan = StringField(max_length=2, required=True)


class OTUMeta(EmbeddedDocument):
    serial = StringField()
    ip_address = StringField()
    netmask = StringField()
    control = IntField()
    answer = IntField()
    link_type = StringField(choices=["Digital", "Analogo", "3G", "4G", "5G"])
    link_owner = StringField(choices=["Propio", "Compartido"])


class OTU(EmbeddedDocument):
    oid = StringField(regex=r"X\d{5}0", min_length=7, max_length=7, required=True)
    metadata = EmbeddedDocumentField(OTUMeta)
    programs = EmbeddedDocumentListField(OTUProgramItem)
    junctions = EmbeddedDocumentListField(Junction, required=True)


class ActionsLog(Document):
    meta = {"collection": "ActionsLog"}
    user = StringField(required=True)
    context = StringField(required=True)
    action = StringField(required=True)
    origin = StringField(required=True)
    date = DateTimeField(default=datetime.now)


class Project(Document):
    meta = {"collection": "Project"}
    metadata = EmbeddedDocumentField(ProjectMeta, required=True)
    oid = StringField(
        regex=r"X\d{5}0",
        min_length=7,
        max_length=7,
        required=True,
        unique=True,
        unique_with=("metadata.version", "metadata.status"),
    )
    otu = EmbeddedDocumentField(OTU, required=True)
    controller = EmbeddedDocumentField(Controller)
    headers = EmbeddedDocumentListField(HeaderItem)
    ups = EmbeddedDocumentField(UPS)
    poles = EmbeddedDocumentField(Poles)
    observation = EmbeddedDocumentField(Comment)


class PlanParseFailedMessage(Document):
    meta = {"collection": "PlanParseFailedMessage"}
    date = DateTimeField(default=datetime.now, required=True)
    plans = ListField(StringField(), required=True)
    comment = EmbeddedDocumentField(Comment, required=True)


class APIKeyUsers(Document):
    meta = {"collection": "APIKeyUsers"}
    key = StringField(required=True, unique=True)
    secret = StringField(required=True)
