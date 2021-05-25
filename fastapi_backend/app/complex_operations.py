import base64
import magic
import dacot_models as dm
from graphql_models import *

class ProjectInputToProject:
	def __init__(self, current_user):
		self.__user = current_user

	def __get_current_user(self):
		return self.__user

	def __is_valid_base64(self, b64s):
		try:
        	return base64.b64encode(base64.b64decode(b64s)) == b64s
    	except Exception:
        	return False

	def __get_b64file_data(self, base64data):
		if not self.__is_valid_base64(base64data):
			raise ValueError('Invalid base64 data')
        _, filedata = base64data.split(",")
        b64bytes = base64.b64decode(filedata)
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
		mname = metain.maintainer
		maintainer = dm.ExternalCompany.objects(name=mname).first()
		if not maintainer:
			raise ValueError('Company {} not found'.format(mname))
		m.maintainer = maintainer
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
		j.metadata = meta
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
			otu.meta = self.__build_otu_meta(data)
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
			h = dm.ProjectHeaderItem()
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

	def parse(data):
		try:
			return True, self.__build_project(data)
		except Exception as excep:
			return False, str(excep)
