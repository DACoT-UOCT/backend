import base64
import magic
import dacot_models as dm
from config import settings
from graphql_models import *
from fastapi_mail import FastMail, MessageSchema
from fastapi.logger import logger
import traceback

class EmailSender:
    def __init__(self, gqlcontext):
        self.__subj = None
        self.__tgts = None
        self.__tname = None
        self.__ctx = gqlcontext

    def __get_proj_commune_maintainer(self, project):
        user = project.metadata.commune.user_in_charge
        if user != None:
            return user.email
        log_commune_obj = project.metadata.commune.to_mongo().to_dict()
        logger.warning('EmailSender_WARNING. Missing user_in_charge for commune {}'.format(log_commune_obj))
        return None

    def __build_email_targets(self, project):
        res = [ project.metadata.status_user.email ]
        comm_maintainer = self.__get_proj_commune_maintainer(project)
        if comm_maintainer:
            res = res + [ comm_maintainer ]
        if len(settings.mail_extra_targets) >= 1:
            res = res + settings.mail_extra_targets
        return res

    def __do_send_email(self, data):
        # TODO: Image??
        background = self.__ctx['background']
        msg = MessageSchema(subject=self.__subj, recipients=self.__tgts, body=data, subtype='html')
        fm = FastMail(settings.mail_config)
        background.add_task(fm.send_message, msg, template_name=self.__tname)

    def send_update_created(self, project):
        try:
            self.__subj = '[DACoT.UOCT] Nueva Actualización {}'.format(project.oid)
            self.__tgts = self.__build_email_targets(project)
            self.__tname = 'update_created.html'
            self.__do_send_email({
                'title': self.__subj,
                'name': project.metadata.status_user.full_name,
                'message': project.observation.message
            })
            return True, None
        except Exception as excep:
            return False, str(excep)

    def send_update_accepted(self, project, message=None, img=None):
        if not message:
            message = 'Sin Observaciones'
        try:
            self.__subj = '[DACoT.UOCT] Actualización {} ACEPTADA'.format(project.oid)
            self.__tgts = self.__build_email_targets(project)
            self.__tname = 'update_accepted.html'
            self.__do_send_email({
                'title': self.__subj,
                'name': project.metadata.status_user.full_name,
                'message': message
            })
            return True, None
        except Exception as excep:
            return False, str(excep)

    def send_update_rejected(self, project, message=None, img=None):
        if not message:
            message = 'Sin Observaciones'
        try:
            self.__subj = '[DACoT.UOCT] Actualización {} RECHAZADA'.format(project.oid)
            self.__tgts = self.__build_email_targets(project)
            self.__tname = 'update_rejected.html'
            self.__do_send_email({
                'title': self.__subj,
                'name': project.metadata.status_user.full_name,
                'message': message
            })
            return True, None
        except Exception as excep:
            return False, str(excep)

    def send_new_created(self, project):
        try:
            self.__subj = '[DACoT.UOCT] Nuevo Proyecto {}'.format(project.oid)
            self.__tgts = self.__build_email_targets(project)
            self.__tname = 'new_created.html'
            self.__do_send_email({
                'title': self.__subj,
                'name': project.metadata.status_user.full_name,
                'message': project.observation.message
            })
            return True, None
        except Exception as excep:
            return False, str(excep)

    def send_new_accepted(self, project, message=None, img=None):
        if not message:
            message = 'Sin Observaciones'
        try:
            self.__subj = '[DACoT.UOCT] Nuevo Proyecto {} ACEPTADO'.format(project.oid)
            self.__tgts = self.__build_email_targets(project)
            self.__tname = 'new_accepted.html'
            self.__do_send_email({
                'title': self.__subj,
                'name': project.metadata.status_user.full_name,
                'message': message
            })
            return True, None
        except Exception as excep:
            return False, str(excep)

    def send_new_rejected(self, project, message=None, img=None):
        if not message:
            message = 'Sin Observaciones'
        try:
            self.__subj = '[DACoT.UOCT] Nuevo Proyecto {} RECHAZADO'.format(project.oid)
            self.__tgts = self.__build_email_targets(project)
            self.__tname = 'new_rejected.html'
            self.__do_send_email({
                'title': self.__subj,
                'name': project.metadata.status_user.full_name,
                'message': message
            })
            return True, None
        except Exception as excep:
            return False, str(excep)

class ComputeJunctionPlansTables:
    def __init__(self, project):
        self.__proj = project

    def __compute_junc_tables(self, junc):
        max_phid = -1
        isys = {}
        for plan in junc.plans:
            plid = plan.plid
            isys[plid] = {}
            for sys in plan.system_start:
                isys[plid][sys.phid] = sys.value
                if sys.phid > max_phid:
                    max_phid = sys.phid
        eps = {}
        for intg in junc.intergreens:
            intgfrom = ord(intg.phfrom) - 64
            intgto = ord(intg.phto) - 64
            if intgfrom not in eps:
                eps[intgfrom] = {}
            eps[intgfrom][intgto] = int(intg.value)
        evs = {}
        for intg in junc.veh_intergreens:
            intgfrom = ord(intg.phfrom) - 64
            intgto = ord(intg.phto) - 64
            if intgfrom not in evs:
                evs[intgfrom] = {}
            evs[intgfrom][intgto] = int(intg.value)
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
        return final_result

    def __rebuild_junction_plans(self, junc, table):
        new_plans = []
        veh_inters = []
        ped_inters = []
        for inter in junc.intergreens:
            inter_i = dm.JunctionPlanIntergreenValue()
            inter_i.value = int(inter.value)
            inter_i.phfrom = ord(inter.phfrom) - 64
            inter_i.phto = ord(inter.phto) - 64
            ped_inters.append(inter_i)
        for inter in junc.veh_intergreens:
            inter_i = dm.JunctionPlanIntergreenValue()
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
                start_i = dm.JunctionPlanPhaseValue()
                start_i.phid = phid
                start_i.value = row[2]
                starts.append(start_i)
                green_st_i = dm.JunctionPlanPhaseValue()
                green_st_i.phid = phid
                green_st_i.value = row[4]
                green_starts.append(green_st_i)
                veh_g_i = dm.JunctionPlanPhaseValue()
                veh_g_i.phid = phid
                veh_g_i.value = row[5]
                veh_greens.append(veh_g_i)
                ped_g_i = dm.JunctionPlanPhaseValue()
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

    def __update_junction(self, junc):
        try:
            table = self.__compute_junc_tables(junc)
        except Exception as excep:
            raise ValueError('Failed to compute tables for JID={}. {}'.format(junc.jid, str(excep)))
        junc = self.__rebuild_junction_plans(junc, table)
        return junc

    def run(self):
        new_juncs = []
        for junc in self.__proj.otu.junctions:
            new_juncs.append(self.__update_junction(junc))
        self.__proj.otu.junctions = new_juncs
        return self.__proj


class ProjectInputToProject:
    def __init__(self, current_user):
        self.__user = current_user

    def __get_current_user(self):
        return self.__user

    def __is_valid_base64(self, b64s):
        try:
            decoded = base64.b64encode(base64.b64decode(b64s)).decode('utf-8')
            return decoded == b64s
        except Exception:
            return False

    def __get_b64file_data(self, base64data):
        if ',' in base64data:
            _, base64data = base64data.split(",")
        if not self.__is_valid_base64(base64data):
            raise ValueError('Invalid base64 data')
        b64bytes = base64.b64decode(base64data)
        mime = magic.from_buffer(b64bytes[0:2048], mime=True)
        return b64bytes, mime

    def __build_meta(self, data):
        metain = data.metadata
        m = dm.ProjectMeta()
        m.status = data.status
        m.status_user = self.__get_current_user()
        if metain.installation_date:
            m.installation_date = metain.installation_date
        if metain.installation_company:
            cname = metain.installation_company
            comp = dm.ExternalCompany.objects(name=cname).first()
            if not comp:
                raise ValueError('Company {} not found'.format(cname))
            m.installation_company = comp
        commune = dm.Commune.objects(code=metain.commune).first()
        if not commune:
            raise ValueError('Commune {} not found'.format(metain.commune))
        m.commune = commune
        if metain.pedestrian_demand:
            m.pedestrian_demand = metain.pedestrian_demand
        if metain.pedestrian_facility:
            m.pedestrian_facility = metain.pedestrian_facility
        if metain.local_detector:
            m.local_detector = metain.local_detector
        if metain.scoot_detector:
            m.scoot_detector = metain.scoot_detector
        if metain.img:
            fdata, ftype = self.__get_b64file_data(metain.img)
            allowed_img = ['image/jpeg', 'image/png']
            if ftype not in allowed_img:
                raise ValueError('Invalid image type: {}. Allowed: {}'.format(ftype, allowed_img))
            m.img.put(fdata, content_type=ftype)
        if metain.pdf_data:
            fdata, ftype = self.__get_b64file_data(metain.pdf_data)
            allowed_doc = ['application/pdf']
            if ftype not in allowed_doc:
                raise ValueError('Invalid document type: {}. Allowed: {}'.format(ftype, allowed_doc))
            m.pdf_data.put(fdata, content_type=ftype)
        return m

    def __build_otu_meta(self, data):
        metain = data.otu.metadata
        m = dm.OTUMeta()
        if metain.serial:
            m.serial = metain.serial
        if metain.ip_address:
            m.ip_address = metain.ip_address
        if metain.netmask:
            m.netmask = metain.netmask
        if metain.control:
            m.control = metain.control
        if metain.answer:
            m.answer = metain.answer
        if metain.link_type:
            m.link_type = metain.link_type
        if metain.link_owner:
            m.link_owner = metain.link_owner
        return m

    def __build_otu_junction(self, jin):
        j = dm.Junction()
        j.jid = jin.jid
        meta = dm.JunctionMeta()
        meta.sales_id = round((int(j.jid[1:]) * 11) / 13.0)
        meta.address_reference = jin.metadata.address_reference
        meta.location = (jin.metadata.coordinates[0], jin.metadata.coordinates[1])
        if jin.metadata.use_default_vi4:
            meta.use_default_vi4 = jin.metadata.use_default_vi4
        else:
            meta.use_default_vi4 = True
        j.metadata = meta
        if jin.phases:
            j.phases = jin.phases
        if jin.sequence:
            seqs = []
            for seq in jin.sequence:
                s = dm.JunctionPhaseSequenceItem()
                s.phid = seq.phid
                s.phid_system = seq.phid_system
                s.type = seq.type
                seqs.append(s)
            j.sequence = seqs
        if jin.plans:
            plans = []
            for pl in jin.plans:
                p = dm.JunctionPlan()
                p.plid = pl.plid
                p.cycle = pl.cycle
                starts = []
                for st in pl.system_start:
                    s = dm.JunctionPlanPhaseValue()
                    s.phid = st.phid
                    s.value = st.value
                    starts.append(s)
                p.system_start = starts
                plans.append(p)
            j.plans = plans
        if jin.intergreens:
            inters = []
            for inter in jin.intergreens:
                i = dm.JunctionIntergreenValue()
                i.phfrom = inter.phfrom
                i.phto = inter.phto
                i.value = inter.value
                inters.append(i)
            j.intergreens = inters
        return j

    def __build_otu_program(self, pin):
        prog = dm.OTUProgramItem()
        prog.day = pin.day
        prog.time = pin.time
        prog.plan = pin.plan
        return prog

    def __check_junction_coordinates(self, juncs):
        for j in juncs:
            val = len(j.metadata.coordinates)
            if val != 2:
                raise ValueError('Invalid length for coordinates in JID={}. {}'.format(j.jid, val))

    def __build_otu(self, data):
        otuin = data.otu
        self.__check_junction_coordinates(otuin.junctions)
        otu = dm.OTU()
        otu.oid = data.oid
        if otuin.metadata:
            otu.metadata = self.__build_otu_meta(data)
        juncs = []
        for j in otuin.junctions:
            juncs.append(self.__build_otu_junction(j))
        otu.junctions = juncs
        if otuin.program:
            progs = []
            for p in otuin.program:
                progs.append(self.__build_otu_program(p))
            otu.programs = progs
        return otu

    def __build_controller(self, data):
        ctrlin = data.controller
        c = dm.Controller()
        if ctrlin.address_reference:
            c.address_reference = ctrlin.address_reference
        if ctrlin.gps:
            c.gps = ctrlin.gps
        comp = dm.ExternalCompany.objects(name=ctrlin.model.company).first()
        if not comp:
            raise ValueError('Company {} not found'.format(ctrlin.model.company))
        model = dm.ControllerModel.objects(
            company=comp,
            model=ctrlin.model.model,
            firmware_version=ctrlin.model.firmware_version,
            checksum=ctrlin.model.checksum
        ).first()
        if not model:
            raise ValueError('Model {} not found'.format(ctrlin.model.model))
        c.model = model
        return c

    def __build_observation(self, data):
        obs = dm.Comment()
        obs.author = self.__get_current_user()
        obs.message = data.observation
        return obs

    def __build_headers(self, data):
        hds = []
        for hd in data.headers:
            h = dm.HeaderItem()
            h.hal = hd.hal
            h.led = hd.led
            h.type = hd.type
            hds.append(h)
        return hds

    def __build_ups(self, data):
        upsin = data.ups
        u = dm.UPS()
        u.brand = upsin.brand
        u.model = upsin.model
        u.serial = upsin.serial
        u.capacity = upsin.capacity
        u.charge_duration = upsin.charge_duration
        return u

    def __build_poles(self, data):
        pin = data.poles
        p = dm.Poles()
        p.hooks = pin.hooks
        p.vehicular = pin.vehicular
        p.pedestrian = pin.pedestrian
        return p

    def __build_project(self, data):
        p = dm.Project()
        p.oid = data.oid
        p.metadata = self.__build_meta(data)
        p.otu = self.__build_otu(data)
        p.controller = self.__build_controller(data)
        if data.headers:
            p.headers = self.__build_headers(data)
        if data.ups:
            p.ups = self.__build_ups(data)
        if data.poles:
            p.poles = self.__build_poles(data)
        p.observation = self.__build_observation(data)
        return p

    def parse(self, data):
        try:
            return True, self.__build_project(data)
        except Exception as excep:
            traceback.print_last()
            return False, str(excep)
