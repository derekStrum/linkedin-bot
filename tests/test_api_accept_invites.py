import requests
from dotenv import load_dotenv
from os.path import join, dirname
from os import getenv
from time import sleep
dotenv_path = join(dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)


class TestAPIAcceptInvites(object):
    def setup_method(self, method):
        print("\n%s:%s" % (type(self).__name__, method.__name__))

    def teardown_method(self, method):
        pass

    def test_accept_invite(self):
        if getenv('LINKEDIN_TEST_PROXY_USER') and getenv('LINKEDIN_TEST_PROXY_PASS'):
            proxy = getenv("LINKDEIN_TEST_PROXY") + ':' + getenv("LINKEDIN_TEST_PROXY_USER") + ':' + getenv('LINKEDIN_TEST_PROXY_PASS')
        else:
            proxy = getenv("LINKDEIN_TEST_PROXY")

        url_post_whoami = getenv("LINKEDIN_SEVER_ADDRESS") + '/whoami'
        url_logs = getenv("LINKEDIN_SEVER_ADDRESS") + '/logs'
        url_connect_with = getenv("LINKEDIN_SEVER_ADDRESS") + '/connect_with'
        url_accept_invites = getenv("LINKEDIN_SEVER_ADDRESS") + '/accept_invites'

        task_id = requests.post(url_post_whoami,
                                    headers={'x-api-key': getenv("API_KEY")},
                                    data={
                                        'username': getenv('LINKEDIN_DEFAULT_EMAIL'),
                                        'password': getenv('LINKEDIN_DEFAULT_PASSWORD'),
                                        'proxy': proxy,
                                        'max_results': 1,
                                    })

        task_id = task_id.json().get('task_id')
        urn_id = None

        for _ in range(99):
            invites = requests.post(url_logs,
                                    headers={'x-api-key': getenv("API_KEY")},
                                    data={
                                        'task_id': task_id
                                    })

            if invites.json().get('info'):
                urn_id = invites.json().get('info').get('user_info', {}).get('urn')
                break

            sleep(10)

        assert urn_id is not None

        resp_invites = requests.post(url_connect_with,
                                       headers={'x-api-key': getenv("API_KEY")},
                                       data={
                                           'username': getenv('LINKEDIN_SECONDARY_EMAIL'),
                                           'password': getenv('LINKEDIN_SECONDARY_PASSWORD'),
                                           'proxy': proxy,
                                           'urn_id': urn_id,
                                       })

        resp_accept_invites = requests.post(url_accept_invites,
                                       headers={'x-api-key': getenv("API_KEY")},
                                       data={
                                           'username': getenv('LINKEDIN_DEFAULT_EMAIL'),
                                           'password': getenv('LINKEDIN_DEFAULT_PASSWORD'),
                                           'proxy': proxy
                                       })

        print('------------------------------')
        print('ACCEPTED INVITES %s (0 does not means accept invites not working!)' % resp_accept_invites.json().get('accept_invites'))
        print('------------------------------')

        assert resp_invites.json().get('success') is True
