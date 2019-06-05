# custom Gunicorn-WSGI application described
# here: http://docs.gunicorn.org/en/stable/custom.html
from __future__ import unicode_literals
from os import path
import subprocess as sp
from api.application import app
import sys
import multiprocessing
import gunicorn.app.base
from gunicorn.six import iteritems


def number_of_workers():
    return (multiprocessing.cpu_count() * 2) + 1


class StandaloneApplication(gunicorn.app.base.BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super(StandaloneApplication, self).__init__()

    def load_config(self):
        config = dict([(key, value) for key, value in iteritems(self.options)
                       if key in self.cfg.settings and value is not None])
        for key, value in iteritems(config):
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


if __name__ == '__main__':
    # First we run some basic tests
    current_dir = path.dirname(path.abspath(__file__))
    child = sp.Popen(['{0}/venv/bin/python3 -m pytest -s {0}/tests/test_base.py'.format(current_dir)], shell=True)
    streamdata = child.communicate()[0]
    rc = child.returncode
    if rc != 0:
        sys.exit(rc)

    options = {
        'bind': '%s:%s' % ('127.0.0.1', '45121'),
        'workers': number_of_workers(),
        'timeout': 120,
        'graceful_timeout': 120,
        'error-logfile': '/var/log/linkedin_gunicorn_error_log',
    }
    StandaloneApplication(app, options).run()
