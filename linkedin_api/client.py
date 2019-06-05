import requests
import pickle
import logging
from datetime import datetime
from dateutil import parser
from api.utils import query_db, commit_db

logger = logging.getLogger(__name__)


class Client(object):
    """
    Class to act as a client for the Linkedin API.
    """

    # Settings for general Linkedin API calls
    API_BASE_URL = "https://www.linkedin.com/voyager/api"
    REQUEST_HEADERS = {
        "user-agent": " ".join(
            [
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_5)",
                "AppleWebKit/537.36 (KHTML, like Gecko)",
                "Chrome/66.0.3359.181 Safari/537.36",
            ]
        ),
        "x-restli-protocol-version": "2.0.0",
    }

    # Settings for authenticating with Linkedin
    AUTH_BASE_URL = "https://www.linkedin.com"
    AUTH_REQUEST_HEADERS = {
        "X-Li-User-Agent": "LIAuthLibrary:3.2.4 \
                            com.linkedin.LinkedIn:8.8.1 \
                            iPhone:8.3",
        "User-Agent": "LinkedIn/8.8.1 CFNetwork/711.3.18 Darwin/14.0.0",
        "X-User-Language": "en",
        "X-User-Locale": "en_US",
        "Accept-Language": "en-us",
    }

    CONNECTION_TIMEOUT = 60               # Client initialize connection timeout
    LOGIN_DELAY = 3600 * 1                # Do login maximum each hour

    def __init__(self, proxy_dict=None, debug=False, db=None):
        self.session = requests.session()
        self.session.headers = Client.REQUEST_HEADERS
        self.proxies = proxy_dict
        self.session.proxies.update(self.proxies)
        self.session.verify = False
        self.logger = logger

        if not db:
            raise Exception('DB NOT FOUND!')

        self.db = db

    def insert_cookie(self, username, cookie, login_date='', latest_proxy=''):
        latest_proxy = pickle.dumps(self.proxies)
        current_date = str(datetime.utcnow())
        cookies = pickle.dumps(cookie, pickle.HIGHEST_PROTOCOL)

        try:
            if not login_date:
                self.logger.info('setting cookie/date', {'extra': username})

                query_1 = """
INSERT OR IGNORE
INTO
    user (email, cookies, date, latest_proxy) 
VALUES
    (:email, :cookies, :date, :latest_proxy);
"""

                query_2 = """
UPDATE user 
SET
    cookies = :cookies,
    date = :date,
    latest_proxy = :latest_proxy  
WHERE
    email = :email;
"""

                commit_db(self.db, query_1, dict(email=username, cookies=cookies, date=current_date, latest_proxy=latest_proxy))
                commit_db(self.db, query_2, dict(email=username, cookies=cookies, date=current_date, latest_proxy=latest_proxy))
            else:
                query_1 = """
INSERT OR IGNORE
INTO
    user (email, cookies, date, login_date, latest_proxy) 
VALUES
    (:email, :cookies, :date, :login_date, :latest_proxy);
"""
                query_2 = """          
UPDATE user 
SET
    cookies = :cookies,
    date = :date,
    login_date = :login_date,
    latest_proxy = :latest_proxy  
WHERE
    email = :email;
"""
                self.logger.info('setting cookie/date/login_date {0}'.format(login_date), {'extra': username})
                commit_db(self.db, query_1, dict(email=username, cookies=cookies, date=current_date, login_date=login_date, latest_proxy=latest_proxy))
                commit_db(self.db, query_2, dict(email=username, cookies=cookies, date=current_date, login_date=login_date, latest_proxy=latest_proxy))
        except Exception as ex:
            print(ex)

    def get_user(self, username):
        try:
            result = query_db(self.db, 'SELECT * FROM user WHERE email=?', (username,), one=True)
            return result
        except Exception as ex:
            print(ex)

    def _request_session_cookies(self, username):
        """
        Return a new set of session cookies as given by Linkedin.
        """

        try:
            user = self.get_user(username)

            if user and user['cookies']:
                login_date = user['login_date']
                latest_proxy = user['latest_proxy']

                if login_date and latest_proxy:
                    login_difference = (datetime.utcnow() - parser.parse(login_date)).total_seconds()
                    latest_proxy = pickle.loads(latest_proxy)
                    if isinstance(latest_proxy, dict):
                        latest_proxy = {k:v for k, v in latest_proxy.items() if k in ['http', 'https', 'socks4', 'socks5']}

                    proxies_is_equal = latest_proxy == self.proxies
                    if login_difference >= 0 and self.LOGIN_DELAY > login_difference and proxies_is_equal:
                        self.logger.info('{0} sec. until login expire... Use cached login for {1}'.format(self.LOGIN_DELAY - login_difference, username), {'extra': username})
                        cookies = pickle.loads(user['cookies'])
                        return cookies, True

        except FileNotFoundError:
            print("Cookie file not found. Requesting new cookies.")

        res = requests.get(
            f"{Client.AUTH_BASE_URL}/uas/authenticate",
            headers=Client.AUTH_REQUEST_HEADERS,
            proxies=self.proxies,
            verify=False,
            timeout=Client.CONNECTION_TIMEOUT
        )

        return res.cookies, False

    def _set_session_cookies(self, user, cookiejar, login_date=None):
        """
        Set cookies of the current session and save them to a file.
        """
        self.session.cookies = cookiejar
        self.session.headers["csrf-token"] = self.session.cookies["JSESSIONID"].strip('"')
        self.insert_cookie(user, cookiejar, login_date)

    def authenticate(self, username, password):
        """
        Authenticate with Linkedin.

        Return a session object that is authenticated.
        """
        user_data, skiplogin = self._request_session_cookies(username)
        if skiplogin:
            self.logger.info('Skipping login...', {'extra': username})
            self.session.cookies = user_data
            self.session.headers["csrf-token"] = user_data["JSESSIONID"].strip('"')
            return

        self._set_session_cookies(username, user_data, login_date=None)

        payload = {
            "session_key": username,
            "session_password": password,
            "JSESSIONID": self.session.cookies["JSESSIONID"],
        }

        res = requests.post(
            f"{Client.AUTH_BASE_URL}/uas/authenticate",
            data=payload,
            cookies=self.session.cookies,
            headers=Client.AUTH_REQUEST_HEADERS,
            proxies=self.proxies,
            verify=False,
            timeout=Client.CONNECTION_TIMEOUT
        )

        data = res.json()

        # TODO raise better exceptions
        if res.status_code != 200:
            raise Exception('Failed to get status code! {0}'.format(res.status_code))
        elif data["login_result"] != "PASS":
            raise Exception()

        # Success login! Need Update login_date
        self.logger.info('Success!', {'extra': username})
        self._set_session_cookies(username, res.cookies, login_date=datetime.utcnow())
