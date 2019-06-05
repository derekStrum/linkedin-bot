import os
from dotenv import load_dotenv
import sqlite3
import logging

PYTHON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'venv', 'bin', 'python3'))
APP_ROOT = os.path.join(os.path.dirname(__file__), '..')   # refers to application_top

logging.basicConfig(level=logging.INFO)


class TestBase(object):
    def setup_method(self, method):
        print("\n%s:%s" % (type(self).__name__, method.__name__))

    def teardown_method(self, method):
        pass

    def test_base(self):
        dotenv_path = os.path.join(APP_ROOT, '.env')
        load_dotenv(dotenv_path)

        con = sqlite3.connect(os.getenv('DB_NAME'))
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        data = [dict(row) for row in cur.fetchall()]
        tables = [result['name'] for result in data if 'name' in result]
        print('Clean not finished/broken tasks...')
        cur.execute("""
           UPDATE tasks
           SET state=2
           WHERE state=0
        """)
        con.commit()
        cur.close()
        assert any(x in tables for x in ['blacklists', 'codes', 'tasks', 'user'])
