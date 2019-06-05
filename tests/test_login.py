import requests
from dotenv import load_dotenv
from os.path import join, dirname
from os import getenv

dotenv_path = join(dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)


class TestBase(object):
    def setup_method(self, method):
        print("\n%s:%s" % (type(self).__name__, method.__name__))

    def teardown_method(self, method):
        pass

    def test_server_ip(self):
        "GET request to url returns a 200"
        url = getenv("LINKEDIN_SEVER_ADDRESS")
        resp = requests.post(url,  headers={'x-api-key': getenv("API_KEY")})
        assert resp.status_code == 201


    def test_db_get(self):
        "HTTP requests should be redirected to HTTPS"
        url = getenv("LINKEDIN_SEVER_ADDRESS") + '/logs'
        resp = requests.post(url,
                             headers={'x-api-key': getenv("API_KEY")},
                             data={
                                 'username': getenv('LINKEDIN_DEFAULT_EMAIL'),
                                 'section': 'full',
                                 'max_results': 3
                             })

        assert resp.status_code == 201 and 'log_data' in resp.json() and 'user' in resp.json()


    def test_proxy(self):
        if getenv('LINKEDIN_TEST_PROXY_USER') and getenv('LINKEDIN_TEST_PROXY_PASS'):
            proxy = getenv("LINKEDIN_TEST_PROXY_USER") + ':' + getenv('LINKEDIN_TEST_PROXY_PASS') + '@' + getenv("LINKDEIN_TEST_PROXY")
        else:
            proxy = getenv("LINKDEIN_TEST_PROXY")

        proxies = {
            'http': 'http://' + proxy,
            'https': 'https://' + proxy,
        }

        resp = requests.get(getenv('PROXY_TEST_URL'), proxies=proxies)

        assert resp.status_code == 200

    def test_login(self):
        if getenv('LINKEDIN_TEST_PROXY_USER') and getenv('LINKEDIN_TEST_PROXY_PASS'):
            proxy = getenv("LINKDEIN_TEST_PROXY") + ':' + getenv("LINKEDIN_TEST_PROXY_USER") + ':' + getenv('LINKEDIN_TEST_PROXY_PASS')
        else:
            proxy = getenv("LINKDEIN_TEST_PROXY")

        url = getenv("LINKEDIN_SEVER_ADDRESS") + '/login'

        resp = requests.post(url,
                             headers={'x-api-key': getenv("API_KEY")},
                             data={
                                 'username': getenv('LINKEDIN_DEFAULT_EMAIL'),
                                 'password': getenv('LINKEDIN_DEFAULT_PASSWORD'),
                                 'proxy': proxy,
                                 'auto_fill_code': 'true'
                             })

        print(resp.status_code)
        assert resp.status_code == 201 and resp.json()['api_is_working'] == True


