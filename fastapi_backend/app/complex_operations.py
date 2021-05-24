from graphql_models import *

class ProjectInputToProject:

	def parse(data):
		return False, 'ErrorStr'



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

