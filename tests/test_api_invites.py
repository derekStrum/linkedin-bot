import requests
from dotenv import load_dotenv
from os.path import join, dirname
from os import getenv
from random import choice
from time import sleep

dotenv_path = join(dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

invite_messages = [
    '{firstname} {lastname}, can we connect?',
    'Hello {firstname}!',
    'Hello {firstname} {lastname}!',
]

keywords_messages = [
    'python',
    'javascript',
    'java',
    'php'
]


class TestAPIInvites(object):
    def setup_method(self, method):
        print("\n%s:%s" % (type(self).__name__, method.__name__))

    def teardown_method(self, method):
        pass

    def test_invites(self):
        invites_sent = 0
        if getenv('LINKEDIN_TEST_PROXY_USER') and getenv('LINKEDIN_TEST_PROXY_PASS'):
            proxy = getenv("LINKDEIN_TEST_PROXY") + ':' + getenv("LINKEDIN_TEST_PROXY_USER") + ':' + getenv('LINKEDIN_TEST_PROXY_PASS')
        else:
            proxy = getenv("LINKDEIN_TEST_PROXY")

        url_post_invites = getenv("LINKEDIN_SEVER_ADDRESS") + '/send_invites'
        url_whoami = getenv("LINKEDIN_SEVER_ADDRESS") + '/whoami'
        url_logs = getenv("LINKEDIN_SEVER_ADDRESS") + '/logs'

        resp_invites_1 = requests.post(url_post_invites,
                             headers={'x-api-key': getenv("API_KEY")},
                             data={
                                 'username': getenv('LINKEDIN_DEFAULT_EMAIL'),
                                 'password': getenv('LINKEDIN_DEFAULT_PASSWORD'),
                                 'proxy': proxy,
                                 'keywords': choice(keywords_messages),
                                 'message': choice(invite_messages),
                                 'max_results': 3,
                                 'network_depth': 'F|S|O'
                             })

        task_id_1 = resp_invites_1.json().get('task_id')
        resp_invites_2 = requests.post(url_post_invites,
                                       headers={'x-api-key': getenv("API_KEY")},
                                       data={
                                           'username': getenv('LINKEDIN_DEFAULT_EMAIL'),
                                           'password': getenv('LINKEDIN_DEFAULT_PASSWORD'),
                                           'proxy': proxy,
                                           'keywords': choice(keywords_messages),
                                           'max_results': 3
                                       })
        task_id_2 = resp_invites_2.json().get('task_id')

        sleep(20)  # 3 * 5 + some time to find...

        for _ in range(90):
            invites = requests.post(url_logs,
                                           headers={'x-api-key': getenv("API_KEY")},
                                           data={
                                               'task_id': task_id_1
                                           })

            invites2 = requests.post(url_logs,
                                     headers={'x-api-key': getenv("API_KEY")},
                                     data={
                                         'task_id': task_id_2
                                     })

            if invites.json().get('info') and invites2.json().get('info'):
                invites_sent += len(invites.json().get('info'))
                invites_sent += len(invites2.json().get('info'))
                break

            sleep(10)

        assert resp_invites_1.json().get('success') == True \
               and resp_invites_2.json().get('success') == True

        assert invites_sent == 6