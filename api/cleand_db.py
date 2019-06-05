#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sqlite3
import os
from dotenv import load_dotenv
import logging

DAYS = 30

APP_ROOT = os.path.join(os.path.dirname(__file__), '..')   # refers to application_top
dotenv_path = os.path.join(APP_ROOT, '.env')
load_dotenv(dotenv_path)

logging.basicConfig(level=logging.DEBUG)


def get_db():
    db = sqlite3.connect(os.getenv('DB_NAME'))
    db.row_factory = sqlite3.Row
    return db


def commit_db(db, query, args=(), table_name=''):
    cur = db.execute(query, args)
    logging.info('Deleteted {0} rows from {1}'.format(cur.rowcount, table_name))
    cur.close()
    db.commit()


db = get_db()
commit_db(get_db(), "DELETE FROM tasks WHERE TimeStamp < DATETIME('now', '-{0} day');".format(DAYS), table_name='tasks')