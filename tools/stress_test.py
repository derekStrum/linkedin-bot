#  . ./venv/bin/activate && locust -f tools/stress_test.py
from locust import HttpLocust, TaskSet, task
from dotenv import load_dotenv
from os.path import join, dirname
from os import getenv
dotenv_path = join(dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)
import logging, sys
import json
import csv
from random import choice
from io import StringIO

USER_CREDENTIALS = None


class UserBehavior(TaskSet):
    def on_start(self):
        accounts = StringIO(getenv('LINKEDIN_ACCOUNTS_LIST'))
        reader = csv.reader(accounts, delimiter=',')
        user = choice(list(reader)[0]).split(':')
        self.username = user[0]
        self.password = user[1]
        self.headers = {'x-api-key': getenv('API_KEY')}

        proxies = StringIO(getenv('LINKEDIN_PROXIES_LIST'))
        reader = csv.reader(proxies, delimiter=',')
        proxy = choice(list(reader))
        self.proxy = proxy

        """ on_start is called when a Locust start before any task is scheduled """
        self.login()

    def on_stop(self):
        """ on_stop is called when the TaskSet is stopping """

    def login(self):
        self.client.post("/login",  {"username": self.username, "password": self.password, "proxy": self.proxy, "auto_fill_code": "true"}, headers=self.headers)

    # @task(6)
    # def send_invites(self):
    #     self.client.post("/send_invites")
    #
    # @task(5)
    # def connect_with(self):
    #     self.client.post("/connect_with")
    #
    # @task(4)
    # def send_messages(self):
    #     self.client.post("/send_messages")
    #
    # @task(3)
    # def accept_invites(self):
    #     self.client.post("/accept_invites")
    #
    # @task(2)
    # def post_messages(self):
    #     self.client.post("/post_messages")
    #     self.client.post("/delete_comment")

    @task(1)
    def whoami(self):
        with self.client.post("/whoami",
                              {
                                  "username": self.username,
                                  "password": self.password,
                                  "proxy": self.proxy,
                                  "auto_fill_code": "true"},
                              headers=self.headers, catch_response=True) as response:
            result = json.loads(response.content)
            if result.get('success'):
                response.success()
            else:
                response.failure("Got wrong result %s" % result.get('message'))

    # @task(1)
    # def logs(self):
    #     self.client.post("/logs")

    # with client.get("/", catch_response=True) as response:
    # if response.content != b"Success":
    # response.failure("Got wrong response")
    # response.success()


class WebsiteUser(HttpLocust):
    task_set = UserBehavior
    host = "http://127.0.0.1:45121"
    min_wait = 5000
    max_wait = 100000