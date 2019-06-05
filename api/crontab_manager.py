import functools
import logging
from uuid import uuid4
from crontab import CronTab
from datetime import datetime
from traceback import print_exc
from cron_descriptor import get_description
from time import sleep
import re

logger = logging.getLogger(__name__)


class CrontabManager:
    """
    usage:
        use https://crontab.guru to generate crontab
        crontab = CrontabManager()
        job = crontab.create_job('15 14 1 * *', 'curl', username)
        job_id = job.get('job_id')
        print(crontab.check_job(job_id))
        crontab.delete_job(job_id)
        crontab.delete_job(job_id)
        print(crontab.check_job(job_id))
    """
    def __init__(self, debug=False):
        self.is_writing = False
        logging.basicConfig(level=logging.WARNING if debug else logging.WARNING)
        self.cron = CronTab(user=True)

    def cron_check(self, setall_string, command):
        desc = None
        is_valid = False
        try:
            desc = get_description(setall_string)
            if desc:
                is_valid = True

            if not command.startswith('curl'):
                error = 'Only curl allowed!'
        except Exception:
            pass

        return is_valid, desc

    def create_job(self, setall_string, command, username):
        description = None
        cron_job = None
        skip = False

        try:
            if not all([setall_string, command]):
                return False

            cron_valid, description = self.cron_check(str(setall_string), command)

            # Checking old cronjobs
            jobs = self.cron.find_comment(re.compile('_' + re.escape(username)))
            for job in jobs:
                if job.slices == setall_string and job.command == command:
                    skip = True
                    cron_job = job
                    logger.info('Skipping creating job for {0}. Same job with setall_string / command / user exist!'.format(username), {'extra': username})
                    break

            if cron_valid and not skip:
                job_id = datetime.utcnow().strftime("%s") + '_' + str(uuid4()) + '_' + username
                cron_job = self.cron.new(command=command, comment=job_id)
                cron_job.setall(setall_string)
                self.cron.write()

        except Exception:
            print_exc()
            pass
            return None

        if cron_job:
            return {
                'job_id': cron_job.comment,
                'job_frequency': description,
                'job_command': cron_job.command,
                'job_skipped': skip
            }

    def delete_job(self, job_id):
        del_status = self.cron.remove_all(comment=job_id)
        self.cron.write()
        return del_status

    def check_job(self, job_id):
        jobs = self.cron.find_comment(job_id)
        jobs_data = []
        for job in jobs:
            if job.comment and job.command:
                jobs_data.append({
                   job.comment: job.command
                })

        return jobs_data

