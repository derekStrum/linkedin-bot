from flask import make_response
JSON_MIME_TYPE = 'application/json'
import pickle
import re
import time
import email
import requests
from subprocess import Popen, PIPE
from imapclient import IMAPClient
from bs4 import BeautifulSoup
from traceback import print_exc
import os
from datetime import datetime

imap_database = {
    'gmail.com': ['imap.gmail.com', 993],
    'inomoz.ru': ['imap.gmail.com', 993],
    'htomail.com': ['imap-mail.outlook.com', 993],
    'outlook.com': ['imap-mail.outlook.com', 993],
    'ya.ru': ['imap.yandex.ru', 993],
    'aol.com': ['imap.aol.com', 993],
}


def json_response(data='', status=200, headers=None):
    headers = headers or {}
    if 'Content-Type' not in headers:
        headers['Content-Type'] = JSON_MIME_TYPE

    return make_response(data, status, headers)


def query_db(db, query, args=(), one=False):
    # db.set_trace_callback(print)
    cur = db.execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def commit_db(db, query, args=()):
    # db.set_trace_callback(print)
    cur = db.execute(query, args)
    cur.close()
    db.commit()


def save_user_data(db, user, headers, cookies, results):
    headers = pickle.dumps(headers, pickle.HIGHEST_PROTOCOL)
    cookies = pickle.dumps(cookies, pickle.HIGHEST_PROTOCOL)
    results = pickle.dumps(results, pickle.HIGHEST_PROTOCOL)
    query = """INSERT OR REPLACE INTO codes (email, results, headers, cookies)
VALUES (:email, :results, :headers, :cookies)"""
    commit_db(db, query, dict(email=user, results=results, headers=headers, cookies=cookies))


def get_user_data(db, user):
    data = query_db(db, "SELECT * FROM codes WHERE email = :email",
                    dict(email=user), one=True)


    results = pickle.loads(data['results'])
    headers = pickle.loads(data['headers'])
    cookies = pickle.loads(data['cookies'])

    return headers, cookies, results


def get_code(email_message):
    match_1 = []
    match_2 = []
    for part in email_message.walk():
        if part.get_content_type() == "text/html":
            body = part.get_payload(decode=True).decode()
            # TODO: match only 6 digits?
            match_1 = re.findall(r'код подтверждения для завершения входа\: (\d+)', body)
            match_2 = re.findall(r'Please use this verification code to complete your sign in\: (\d+)', body)

    if len(match_1) >= 1:
        return match_1[0]
    elif len(match_2) >= 1:
        return match_2[0]
    else:
        return None


def check_email(user, password, timeout=0, server=None):
    time.sleep(timeout)
    code = None

    if not server:
        domain = user.split('@')[1]
        if domain in imap_database:
            server = IMAPClient(imap_database[domain][0], port=imap_database[domain][1])
            server.login(user, password)
        else:
            raise ValueError('Unknown email domain!')

    select_info = server.select_folder('INBOX')
    print('%d messages in INBOX' % select_info[b'EXISTS'])
    messages = server.search(['UNSEEN', 'FROM', 'security-noreply@linkedin.com'])
    messages_len = len(messages)
    i = 0
    for uid, message_data in server.fetch(messages, 'RFC822').items():
        i += 1

        if i == messages_len:
            email_message = email.message_from_bytes(message_data[b'RFC822'])
            code = get_code(email_message)

    if server:
        server.logout()

    return code


def send_login_data(client, CHECKPOINT_URL, results):
    resp = client.post(CHECKPOINT_URL, data=results, verify=False)
    success = False

    if not 'challenge/verify' in resp.url and not 'checkpoint/lg' in resp.url:
        message = 'Successfully logged-in with filling pin code!'
        success = True
    else:
        print(resp.url)
        message = 'Failed to login... Try again'

    return success, message


def linkedin_login(proxy, user, password, email_user, email_password, ua='', db=None, code=None, cookies=None, auto_fill_code=False, timeout=10):
    success = False
    message = ''
    links = {}
    links['HOMEPAGE_URL'] = os.getenv('HOMEPAGE_URL')
    links['LOGIN_URL'] = os.getenv('LOGIN_URL')
    links['CHECKPOINT_URL'] = os.getenv('CHECKPOINT_URL')

    if not isinstance(proxy, dict) and not proxy.get('http') and not proxy.get('https'):
        message = 'Unknow proxy format'
        return success, message

    if not all([links.get('HOMEPAGE_URL'), links.get('LOGIN_URL'), links.get('CHECKPOINT_URL')]):
        message = 'Check your env file!'
        return success, message

    HOMEPAGE_URL = links.get('HOMEPAGE_URL')
    LOGIN_URL = links.get('LOGIN_URL')
    CHECKPOINT_URL = links.get('CHECKPOINT_URL')

    with requests.Session() as client:
        if code:
            headers, cookies, results = get_user_data(db, user)
            client.proxies = proxy
            client.headers = headers
            client.cookies = cookies
            results['pin'] = code

            if not all([headers, cookies, results]):
                message = 'Failed to load some data from db (headers, cookies, results)'
                return success, message

            success, message = send_login_data(client, CHECKPOINT_URL, results)
        else:
            client.proxies = proxy
            client.headers = {'User-Agent': ua}

            try:
                res = client.get(HOMEPAGE_URL, verify=False, timeout=timeout)
                html = res.content
                soup = BeautifulSoup(html, 'html.parser')

                login_inputs = soup.find_all('input', {'type': 'hidden'})
                login_results = {}

                for txt_input in login_inputs:
                    name = txt_input.get('name')
                    value = txt_input.get('value')
                    if name and value:
                        login_results[name] = value

                if login_results.get('csrfToken') and login_results.get('loginCsrfParam'):
                    login_results['session_key'] = user
                    login_results['session_password'] = password

                    keyorder = ['csrfToken',
                                'session_key',
                                'ac',
                                'sIdString',
                                'controlId',
                                'parentPageKey',
                                'pageInstance',
                                'trk',
                                'session_redirect',
                                'loginCsrfParam',
                                'fp_data',
                                '_d',
                                'session_password']

                    login_results = dict(sorted(login_results.items(), key=lambda i:keyorder.index(i[0])))
                    resp = client.post(LOGIN_URL, data=login_results, verify=False)

                    if 'errorKey' in resp.url:
                        message = 'Failed to login, check your proxy/account/or_try_later'

                    elif '/feed' in resp.url:
                        message = 'Successfully logged-in'
                        success = True

                    elif 'add-phone?country_code' in resp.url:
                        message = 'Successfully logged-in. Result url {0}'.format(resp.url)
                        success = True

                    elif 'checkpoint/challenge' in resp.url:
                        soup = BeautifulSoup(resp.content, 'html.parser')
                        inputs = soup.find_all('input', {'type': 'hidden'})
                        results = {}

                        for txt_input in inputs:
                            name = txt_input.get('name')
                            value = txt_input.get('value')
                            if name and value:
                                results[name] = value

                        if results.get('pageInstance') and 'urn:li:page:d_checkpoint_ch_emailPinChallenge' in results.get('pageInstance'):
                            # First we save user data
                            save_user_data(db=db, user=user, results=results, headers=client.headers, cookies=client.cookies)

                            # We get code from email
                            if auto_fill_code:
                                print('Wait %s seconds...' % 20)
                                time.sleep(20)
                                code = check_email(email_user, email_password)
                                results['pin'] = code
                                success, message = send_login_data(client, CHECKPOINT_URL, results)
                            else:
                                 success = 'need_key'
                                 message = 'Need send pin key to /send_key with %s username' % user

                        elif results.get('captchaSiteKey'):
                            message = 'Captcha key found, captcha solving not implemented!'
                        else:
                            message = 'Challenge page changed? need check %s' % results
                else:
                    message = 'csrf value not found on %s' % HOMEPAGE_URL
            except Exception as e:
                print_exc()
                message = 'Unknow error %s' % str(e)
                pass

    return success, message


def run_tests_in_background(APP_ROOT, log_file_path, names='tests/test_login.py tests/test_api*.py'):
    Popen(
        ['{0}/venv/bin/python3 -m pytest -q -s {1} > {2}'.format(APP_ROOT, names, log_file_path)],
        shell=True,
        stdout=PIPE
    )


def user_reset(db, user):
    query = """
            UPDATE
                user 
            SET
                cookies = NULL,
                date = :date,
                login_date = null,
                latest_proxy = null 
            WHERE
                email=:email
            """
    time = datetime.utcnow()
    commit_db(db, query, dict(email=user, date=time))


def insert_or_replace_task(db, task_id, timestamp, user, type, state):
    """
    :param db:
    :param task_id:
    :param timestamp:
    :param user:
    :param type:
    :param state:
    :return:

    insert or replace task_id, states: 0 task is running, 1 task is finished, 2 task is finished with error
    """
    query = """
    INSERT OR REPLACE INTO tasks (task_id, timestamp, username, type, state)
    VALUES (:task_id, :timestamp, :username, :type, :state);
    """
    commit_db(db,
              query,
              dict(task_id=task_id, timestamp=timestamp, username=user, type=type, state=state))