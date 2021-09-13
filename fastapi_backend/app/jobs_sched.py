from pytz import utc
import dacot_models as dm
from .config import get_settings
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from .graphql_mutations import SyncProjectFromControl
from .graphql_models import GetProjectInput

def generate_updates_job():
    dm.PlanParseFailedMessage.drop_collection()
    prods = dm.Project.objects(metadata__status='PRODUCTION', metadata__version='latest')
    c = 0
    for proj in prods:
        scheduler.update(proj.oid)
        c += 1
    print('We have created {} jobs for project updates'.format(c))
    scheduler.info()

def update_project_job(oid):
    data = GetProjectInput()
    data.oid = oid
    data.status = 'PRODUCTION'
    mut = SyncProjectFromControl()
    res = mut.mutate(None, None, data)
    if res.code != 200:
        raise RuntimeError(res.message)

def listener(event):
    if event.exception:
        print('Job [{}] has failed with the error: {}'.format(event.job_id, event.exception))
    else:
        print('Job [{}] has succeded'.format(event.job_id))

class DACoTJobsScheduler:
    def __init__(self):
        jobstores = {
            'default': SQLAlchemyJobStore(url=get_settings().sched_jobs_db)
        }
        executors = {
            'default': ThreadPoolExecutor(1),
        }
        job_defaults = {
            'coalesce': True,
            'max_instances': 1
        }
        self.__scheduler = AsyncIOScheduler(jobstores=jobstores, executors=executors, job_defaults=job_defaults, timezone=utc)
        self.__scheduler.add_listener(listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        self.__scheduler.add_job(generate_updates_job, trigger=CronTrigger.from_crontab('0 22 * * SUN'), id='junction_updates_generator', replace_existing=True)
        self.info()

    def start(self):
        self.__scheduler.start()

    def update(self, oid):
        self.__scheduler.add_job(update_project_job, trigger='date', kwargs={'oid': oid}, id='project_update_{}'.format(oid), replace_existing=True, misfire_grace_time=None)

    def info(self):
        self.__scheduler.print_jobs()

scheduler = DACoTJobsScheduler()
