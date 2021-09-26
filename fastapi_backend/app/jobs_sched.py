import time
import random
import datetime
from pytz import utc, timezone
import dacot_models as dm
from .config import get_settings
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from .graphql_mutations import SyncProjectFromControl
from .graphql_models import GetProjectInput

QUEUE_DATA = dict()

SYNC_INTERVAL_UTC_TIME_START = 20 # (23 SCL)
SYNC_INTERVAL_UTC_TIME_STOP = 4 # (7 SCL)
DAYS_SINCE_LAST_SYNC_LIMIT = 20

def generate_updates_job():
    print('Starting generate_updates_job')
    dm.PlanParseFailedMessage.drop_collection()
    prods = dm.Project.objects(metadata__status='PRODUCTION', metadata__version='latest')
    to_update = []
    for proj in prods:
        if proj.metadata.last_sync_date > (datetime.datetime.utcnow() - datetime.timedelta(days=DAYS_SINCE_LAST_SYNC_LIMIT)):
            print('Skipping update job for {}. Project.metadata.last_sync_date < DAYS_SINCE_LAST_SYNC_LIMIT'.format(proj.oid))
            continue
        to_update.append(proj.oid)
    random.shuffle(to_update)
    for item in to_update:
        print('Added update job for {} to scheduler'.format(item))
        scheduler.update(item)
        if item not in QUEUE_DATA:
            QUEUE_DATA[item] = {
                'num_retry': 0,
                'time': 0,
                'done': False
            }
        QUEUE_DATA[item]['num_retry'] = QUEUE_DATA[item]['num_retry'] + 1
    print('We have created {} jobs for project updates'.format(len(to_update)))

def update_project_job(oid):
    print('Starting update for {}'.format(oid))
    current_hour = int(datetime.datetime.utcnow().hour)
    r = range(SYNC_INTERVAL_UTC_TIME_STOP, SYNC_INTERVAL_UTC_TIME_START + 1)
    if current_hour not in r:
        print('Skipping update job for {}. Not in sync range hours. ({} | {})'.format(oid, current_hour, r))
    proj = dm.Project.objects(metadata__status='PRODUCTION', metadata__version='latest', oid=oid).first()
    assert proj != None
    if proj.metadata.last_sync_date > (datetime.datetime.utcnow() - datetime.timedelta(days=DAYS_SINCE_LAST_SYNC_LIMIT)):
        print('Skipping update job for {}. Project.metadata.last_sync_date < DAYS_SINCE_LAST_SYNC_LIMIT'.format(oid))
        return
    start = time.time()
    data = GetProjectInput()
    data.oid = oid
    data.status = 'PRODUCTION'
    mut = SyncProjectFromControl()
    res = mut.mutate(None, None, data)
    end = time.time()
    if res.code != 200:
        raise RuntimeError(res.message)
    if oid in QUEUE_DATA:
        QUEUE_DATA[oid]['time'] = int(end - start)
        QUEUE_DATA[oid]['done'] = True
    print('Update for {} done'.format(oid))

def listener(event):
    if event.exception:
        print('[=>][!] Job [{}] has failed with the error: {}'.format(event.job_id, event.exception))
    else:
        print('[=>][+] Job [{}] has succeded'.format(event.job_id))
    not_done = list(filter(lambda x: not x[1]['done'], QUEUE_DATA.items()))
    done = list(filter(lambda x: x[1]['done'], QUEUE_DATA.items()))
    print('We have {} projects to update'.format(len(not_done)))
    if len(done) > 0:
        avg = int(sum(map(lambda x: x[1]['time'], done)) / len(done))
        print('The average time is {}s'.format(avg))

def clock():
    print('The time is: {}'.format(datetime.datetime.now()))
    print('The time is (UTC): {}'.format(datetime.datetime.utcnow()))

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
            'max_instances': 10_000_000
        }
        self.__scheduler = AsyncIOScheduler(jobstores=jobstores, executors=executors, job_defaults=job_defaults, timezone=timezone('America/Santiago'))
        self.__scheduler.add_listener(listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        self.__scheduler.add_job(generate_updates_job, trigger=CronTrigger.from_crontab('*/5 * * * *'), id='junction_updates_generator', replace_existing=True)
        self.__scheduler.add_job(clock, trigger='interval', minutes=5, id='clock', replace_existing=True)
        self.info()

    def start(self):
        self.__scheduler.start()

    def update(self, oid):
        self.__scheduler.add_job(update_project_job, args=[oid], trigger='date', id='project_update_{}'.format(oid), replace_existing=True, misfire_grace_time=None)

    def info(self):
        self.__scheduler.print_jobs()

scheduler = DACoTJobsScheduler()
