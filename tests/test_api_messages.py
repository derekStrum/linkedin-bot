import requests
from dotenv import load_dotenv
from os.path import join, dirname
from os import getenv
from random import choice, uniform

dotenv_path = join(dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

thanks_words = [
    'Thanks.',
    'Fine',
    'Cool',
    'Awesome',
    'Thank you.',
    'I am indebted to you.',
    'Delicious.',
    'I appreciate you.',
    'You are an inspiration.',
    'I am grateful.',
    'You are a blessing.',
    'You are a true friend.',
    'You\'re so great.',
    'This is great.',
    'You light up my life.',
    'My sincere thanks.',
    'You\'re the best.',
    'You make me happy.',
    'You\'ve been very helpful.'
]


class TestAPIMessages(object):
    def setup_method(self, method):
        print("\n%s:%s" % (type(self).__name__, method.__name__))

    def teardown_method(self, method):
        pass

    def test_send_massage(self):
        if getenv('LINKEDIN_TEST_PROXY_USER') and getenv('LINKEDIN_TEST_PROXY_PASS'):
            proxy = getenv("LINKDEIN_TEST_PROXY") + ':' + getenv("LINKEDIN_TEST_PROXY_USER") + ':' + getenv('LINKEDIN_TEST_PROXY_PASS')
        else:
            proxy = getenv("LINKDEIN_TEST_PROXY")

        url_post = getenv("LINKEDIN_SEVER_ADDRESS") + '/post_messages'
        url_delete = getenv("LINKEDIN_SEVER_ADDRESS") + '/delete_comment'

        resp_post = requests.post(url_post,
                             headers={'x-api-key': getenv("API_KEY")},
                             data={
                                 'username': getenv('LINKEDIN_DEFAULT_EMAIL'),
                                 'password': getenv('LINKEDIN_DEFAULT_PASSWORD'),
                                 'proxy': proxy,
                                 'message': choice(thanks_words),
                                 'post_url': getenv('LINKEDIN_TEST_FEEDS'),
                             })

        uniform(2, 4)

        resp_delete = requests.post(url_delete,
                             headers={'x-api-key': getenv("API_KEY")},
                             data={
                                 'username': getenv('LINKEDIN_DEFAULT_EMAIL'),
                                 'password': getenv('LINKEDIN_DEFAULT_PASSWORD'),
                                 'proxy': proxy,
                                 'ugc_post': resp_post.json()['restli_id']
                             })

        assert resp_post.json()['success'] == True and resp_delete.json()['success'] == True
