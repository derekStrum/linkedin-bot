import json
import logging
import os
import re
import sqlite3
from datetime import datetime
from logging.config import dictConfig
from logging.handlers import RotatingFileHandler
from random import randint, choice
from threading import Lock
from time import sleep
from traceback import print_exc
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs
from uuid import uuid4

import urllib3
from dotenv import load_dotenv
from flask import Flask, g, request, abort, Response, render_template
from flask_executor import Executor
from api.crontab_manager import CrontabManager
from api.utils import query_db, linkedin_login, run_tests_in_background, user_reset, insert_or_replace_task
from linkedin_api import Linkedin
from linkedin_api.utils.helpers import get_requests_proxies, smart_proxy_parser, parse_mini_profile
from .utils import json_response
from .get_user_agents import get_all_user_agents
from api.utils import commit_db
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


logger = logging.getLogger(__name__)
JSON_MIME_TYPE = 'application/json'

# load dotenv in the base root
APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))   # refers to application_top
dotenv_path = os.path.join(APP_ROOT, '.env')
load_dotenv(dotenv_path)

# Used for writing cronjobs
lock = Lock()

# Disable unsecured warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Flask log configuration
log_dict = {
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'WARNING',
        'handlers': ['wsgi']
    }
}

if os.getenv('FLASK_DEBUG'):
    log_dict['root']['level'] = 'DEBUG'

dictConfig(log_dict)

app = Flask(__name__)
executor = Executor(app)
crontab = CrontabManager()
logger = logging.getLogger('werkzeug')

logger.addHandler(logging.StreamHandler())
logger.addHandler(RotatingFileHandler(
    os.path.join(os.path.dirname(__file__), '..', 'logs', os.getenv('LOGS_FILE')),
    maxBytes=10000000,
    backupCount=1
))

user_agents = get_all_user_agents()

if len(user_agents) <= 0:
    logger.error('NO USER AGENTS FOUND (check get_user_agents.py script)')
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.0.3 Safari/605.1.15'
    ]

# Check API keys
if not os.getenv("API_KEY"):
    raise Exception('NO API KEY!')


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(os.getenv('DB_NAME'))
        db.row_factory = sqlite3.Row

    return db


def require_key(func):
    def func_wrapper(*args, **kwargs):
        key = os.getenv("API_KEY")
        if request.headers.get('x-api-key') and request.headers.get('x-api-key') == key:
            return func(*args, **kwargs)
        else:
            abort(401)
    return func_wrapper


def requires_auth(func):
    def func_wrapper(*args, **kwargs):
        auth = request.authorization
        if not auth or not (auth.username == os.getenv('ADMIN_USER', 'user_not_exist_seoij223') and auth.password == os.getenv('ADMIN_PASS', 'password_not_exist_lwiejf012922')):
            return Response(
                'Could not verify your access level for that URL.\n'
                'You have to login with proper credentials', 401,
                {'WWW-Authenticate': 'Basic realm="Login Required"'})
        else:
            return func(*args, **kwargs)
    return func_wrapper


def generate_curl(request):
    host = os.getenv('LINKEDIN_SEVER_ADDRESS')

    command = """curl -X {method} -H {headers} '{uri}'"""
    method = request.method
    uri = request.url

    u = urlparse(uri)
    u = u._replace(netloc=host)

    if u.scheme != 'http':
        u = u._replace(scheme='http')

    query = parse_qs(u.query)
    query.pop('cronjob_create', None)
    u = u._replace(query=urlencode(query, True))

    uri = urlunparse(u)

    headers = ['"{0}: {1}"'.format(k, v) for k, v in request.headers.items() if k.lower() in [
        'content-type',
        'x-api-key'
    ]]
    headers = " -H ".join(headers)
    command = command.format(method=method, headers=headers, uri=uri)
    return command


def cronjob_generator(success, request, response_data):
    data = request.values
    create_cronjob = data.get('cronjob_create', 'no') in ['true', '1', 't', 'y', 'yes']
    setall_string = data.get('setall_string')
    if success:
        command = generate_curl(request)

        if create_cronjob and command and setall_string and data.get('username'):
            with lock:
                job = crontab.create_job(setall_string, command, data.get('username'))

            if job:
                response_data.update(job)
        elif create_cronjob:
            logger.warning('Check your cron setall_string or command string!',
                           {'extra': data.get('username'), 'section': 'crontab'})

    if create_cronjob and response_data.get('job_id'):
        response_data['cron_generated'] = True
    elif create_cronjob:
        response_data['cron_generated'] = False

    return response_data


def get_api(request, do_force=False):
    message = ''
    api_is_working = False
    linkedin = None

    data = request.values
    username = data.get('username')
    password = data.get('password')
    proxy = data.get('proxy')
    force = data.get('force')
    auto_fill_code = bool(data.get('auto_fill_code', False))

    if not all([username, password, proxy]):
        message = 'Missing some field/s (username, password, proxy)'
        return api_is_working, linkedin, message

    random_user = {'user': username, 'password': password}

    user = random_user['user']
    password = random_user['password']

    if data.get('email_user'):
        email_user = data.get('email_user')
    else:
        email_user = user

    if data.get('email_password'):
        email_password = data.get('email_password')
    else:
        email_password = password

    parsed_proxy = smart_proxy_parser('http://' + proxy)
    requests_proxy = get_requests_proxies(parsed_proxy)

    logger.info('Testing API using {0}'.format(requests_proxy), {'extra': user})
    db = get_db()

    # We trying just login...
    if not (auto_fill_code or force == 'yes' or do_force):
        try:
            linkedin = Linkedin(user, password, proxy_dict=requests_proxy, db=db, logger=logger)
            logger.info('API is working', {'extra': user})
            api_is_working = True
        except Exception as e:
            print_exc()
            pass
    else:
        logging.info('Autofill code is true or we need force login!')

    # If login was not successful we trying warm ip and login
    if not api_is_working:
        try:
            warm_success, message = linkedin_login(proxy=requests_proxy,
                                                   user=user,
                                                   password=password,
                                                   email_user=email_user,
                                                   email_password=email_password,
                                                   db=db,
                                                   ua=choice(user_agents),
                                                   auto_fill_code=auto_fill_code)
            if type(warm_success) == bool and warm_success:
                logger.info('Reseting user', {'extra': user})
                user_reset(db=db, user=user)
                sleep(randint(20, 25))  # we need wait some time after login!
                linkedin = Linkedin(user, password, proxy_dict=requests_proxy, db=db, logger=logger)
                api_is_working = True
            elif warm_success == 'need_code':
                api_is_working = 'need_code'
                logger.info('You need send pin key to `/send_key` with current proxy and user', {'extra': user})
            else:
                api_is_working = warm_success
                logger.info('IP warm not helped, try again or change url', {'extra': user})

        except Exception as e:
            print_exc()
            pass

    return api_is_working, linkedin, message


def send_invites_in_background(send_delay,
                               message,
                               linkedin,
                               max_entries,
                               data,
                               keywords,
                               max_results,
                               black_list,
                               task_id,
                               send_invites_timestamp):
    invites_sent = []
    connection_of = data.get('connection_of')
    network_depth = data.get('network_depth', None) # Depending on network_depth you can send or can't send invite!
    regions = data.getlist('regions[]') # use multiple regions[] as values
    industries = data.getlist('industries[]')

    try:
        print('search peoples', max_results)

        search_results = linkedin.search_people(
            keywords=keywords,
            connection_of=connection_of,
            network_depth=network_depth,
            regions=regions,
            industries=industries,
            max_results=max_results,
            black_list=black_list
        )

        print('sending invites', len(search_results))

        if search_results:
            for i, profile in enumerate(search_results):
                parsed_message = None
                invite_timeout = randint(send_delay, send_delay + 3)  # additional timeout between invites

                if message:
                    parsed_message = profile.get('title', {}).get('text', '')
                    if ' ' in parsed_message:
                        parsed_message = message.format(firstname=parsed_message.split(' ')[0],
                                                        lastname=parsed_message.split(' ')[1])

                invite_success = linkedin.connect_with_someone(profile["urn_id"], message=parsed_message)
                invites_sent.append({
                    'urn_id': profile["urn_id"],
                    'publicIdentifier': profile['public_id'],
                    'success': invite_success,
                })

                if invite_success and i + 1 != max_entries:
                    print('New invite %s' % invite_timeout)
                    sleep(invite_timeout)

                if i + 1 == max_entries:
                    break

            if invites_sent:
                # We need place task id into database, to check it result!
                with app.app_context():
                    db = get_db()
                    query = """
                            INSERT 
                            INTO
                                blacklists
                                (username, invites_sent, timestamp, task_id)         
                            VALUES
                                (:username, :invites_sent, :timestamp, :task_id);
                            """
                    commit_db(db, query, dict(username=data.get('username'),
                                              invites_sent=json.dumps(invites_sent),
                                              timestamp=send_invites_timestamp,
                                              task_id=task_id))

                    insert_or_replace_task(db, task_id, send_invites_timestamp, data.get('username'), 'send_invites', 1)
                    logger.info('New {0} invites for {1}'.format(len(invites_sent), data.get('username')),
                                {'extra': data.get('username'), 'section': 'invite'})
        else:
            logger.warning('Found {0} entries for keywords {1}!, check your keywords'
                           .format(len(search_results), keywords),
                           {'extra': data.get('username')})
            with app.app_context():
                db = get_db()
                insert_or_replace_task(db, task_id, send_invites_timestamp, data.get('username'), 'send_invites', 3)

    except Exception as e:
        logging.error('Failed execute {0} task_id. Reason {1}'.format(task_id, str(e)))

        with app.app_context():
            db = get_db()
            insert_or_replace_task(db, task_id, send_invites_timestamp, data.get('username'), 'send_invites', 2)

        raise


def get_user_connectons_in_background(user, linkedin, max_connections, task_id, timestamp):
    user_data = {}

    try:
        base_info = linkedin.whoami() or {}
        base_info = parse_mini_profile(base_info.get('miniProfile', {}))
        sleep(randint(2, 3))
        additional_info = linkedin.get_profile(urn_id=base_info.get('urn'))

        # we skip some duplicates fields from /me base_info
        additional_info = {k: v for k, v in additional_info.items() if k not in
                           [
                               'firstName',
                               'lastName',
                               'occupation',
                               'publicIdentifier',
                               'picture',
                               'entityUrn',
                               'profilePictureOriginalImage',
                               'profilePicture',
                               'displayPictureUrl'
                           ]}

        user_data['user_info'] = base_info
        user_data['additional_info'] = additional_info
        user_connections = linkedin.get_profile_connections_raw(max_connections) or {}
        user_data['user_connections'] = []
        for connection in user_connections:
            user_data['user_connections'].append(parse_mini_profile(connection))

        user_data['user_connections_count'] = len(user_data['user_connections'])

        with app.app_context():
            db = get_db()
            query = "UPDATE user SET info = :user_data WHERE email=:email;"
            commit_db(db,
                      query,
                      dict(task_id=task_id, user_data=json.dumps(user_data), email=user))

            # mark task success finished
            insert_or_replace_task(db, task_id, timestamp, user, 'whoami', 1)
    except Exception as e:
        # mark task not finished successful
        logging.error('Failed execute {0} task_id. Reason {1}'.format(task_id, str(e)))

        with app.app_context():
            db = get_db()
            insert_or_replace_task(db, task_id, timestamp, user, 'whoami', 2)

        raise


@app.route('/', methods=['POST'], endpoint='home')
@require_key
def home():
    return json_response(json.dumps({'status': 'ok'}), status=201)


@app.route('/linkedin_api_tester')
@requires_auth
def secret_page():
    return render_template('linkedin_api_tester.html')


@app.route('/login', methods=['POST'], endpoint='login')
@require_key
def login():
    api_is_working, linkedin, api_message = get_api(request, do_force=True)
    if type(api_is_working) == str and api_is_working == 'need_code':
        return json_response(json.dumps({'need_enter_code': api_is_working, 'api_message': api_message}), status=201)

    if api_is_working:
        return json_response(json.dumps({'api_is_working': api_is_working, 'api_message': api_message}), status=201)
    else:
        return json_response(json.dumps({'error': 'API is not working! Try again', 'api_message': api_message}), 400)


@app.route('/send_key', methods=['POST'], endpoint='send_key')
@require_key
def send_key():
    data = request.values
    user = data.get('username')
    password = data.get('password')
    email_user = user
    email_password = password
    code = data.get('key')
    proxy = data.get('proxy')
    warm_success = False
    message = ''

    if not all([user, password, code, proxy]):
        error = json.dumps({'error': 'Missing some field/s (username, key)'})
        return json_response(error, 400)

    parsed_proxy = smart_proxy_parser('http://' + proxy)
    requests_proxy = get_requests_proxies(parsed_proxy)

    try:
        warm_success, message = linkedin_login(
            requests_proxy,
            user,
            password,
            email_user,
            email_password,
            db=get_db(),
            code=code
        )
    except Exception:
        print_exc()
        pass

    if not warm_success:
        message = 'code is incorrect or send_key not working or link expired'

    return json_response(json.dumps({'key_is_set': warm_success, 'message': message}), status=201)


@app.route('/send_invites', methods=['POST'], endpoint='send_invites')
@require_key
def send_invites():
    """
    keywords <str> - keywords, comma seperated
    connection_of <str> - urn id of a profile. Only people connected to this profile are returned
    network_depth <str> - the network depth to search within. One of {F, S, or O}
     (first, second and third+ respectively)
    regions <list> - list of Linkedin region ids
    industries <list> - list of Linkedin industry ids

    message optional
    """
    api_is_working, linkedin, api_message = get_api(request)
    success = False
    task_id = None

    if api_is_working and api_is_working != 'need_key':
        data = request.values
        keywords = data.get('keywords')
        max_results = int(data.get('max_results', '49'))
        max_entries = max_results
        message = data.get('message')
        send_delay = int(data.get('send_delay', 1))
        check_previous_invites = data.get('check_previous_invites', 'yes') in ['true', '1', 't', 'y', 'yes']
        black_list = []
        db = get_db()

        if not all([keywords]):
            error = json.dumps({'error': 'Missing some field/s (keywords)'})
            return json_response(error, 400)

        # here we filter old entries!
        if check_previous_invites:
            query = "SELECT * FROM blacklists WHERE username = :email;"
            old_invites = query_db(db, query, dict(email=data.get('username')))

            for invite in old_invites:
                invite_data = json.loads(invite['invites_sent'])
                for item in invite_data:
                    if item.get('urn_id') and item.get('urn_id') not in black_list:
                        black_list.append(item.get('urn_id'))

        print('Search {0} entries, with {1} blacklist entries'.format(max_results, len(black_list)))
        task_id = datetime.utcnow().strftime("%s") + '_' + str(uuid4()) + '_' + data.get('username')
        send_invites_timestamp = datetime.utcnow()

        # We initialize taskid
        insert_or_replace_task(db, task_id, send_invites_timestamp, data.get('username'), 'send_invites', 0)

        # Run in background send invites
        executor.submit(send_invites_in_background,
                        send_delay=send_delay,
                        message=message,
                        linkedin=linkedin,
                        max_entries=max_entries,
                        data=data,
                        keywords=keywords,
                        max_results=max_results,
                        black_list=black_list,
                        task_id=task_id,
                        send_invites_timestamp=send_invites_timestamp)
        success = True

    response_data = {'api_is_working': api_is_working,
                     'success': success,
                     'api_message': api_message,
                     'task_id': task_id
                     }

    response_data = cronjob_generator(success, request, response_data)
    return json_response(json.dumps(response_data), status=201)


@app.route('/connect_with', methods=['POST'], endpoint='connect_with')
@require_key
def connect_with():
    api_is_working, linkedin, api_message = get_api(request)
    success = False

    if api_is_working:
        data = request.values
        urn_id = data.get('urn_id')

        if not all([urn_id]):
            error = json.dumps({'error': 'Missing some field/s (urn_id)'})
            return json_response(error, 400)

        success = linkedin.connect_with_someone(urn_id)

    response_data = {'api_is_working': api_is_working, 'success': success}
    return json_response(json.dumps(response_data), status=201)


@app.route('/get_user_info', methods=['POST'], endpoint='get_user_info')
@require_key
def get_user_info():
    api_is_working, linkedin, api_message = get_api(request)
    success = False
    additional_info = {}

    if api_is_working:
        data = request.values
        public_id = data.get('public_id')
        urn_id = data.get('urn_id')

        if not any([public_id, urn_id]):
            error = json.dumps({'error': 'Missing some field/s (public_id or urn_id)'})
            return json_response(error, 400)

        result = linkedin.get_profile(urn_id=(urn_id or public_id))

        if result.get('experience'):
            success = True
            additional_info = {k: v for k, v in result.items() if k not in
                               [
                                   'firstName',
                                   'lastName',
                                   'occupation',
                                   'publicIdentifier',
                                   'picture',
                                   'entityUrn',
                                   'profilePictureOriginalImage',
                                   'profilePicture',
                                   'displayPictureUrl'
                               ]}

    response_data = {'api_is_working': api_is_working, 'success': success}

    if additional_info:
        response_data['additional_info'] = additional_info
    else:
        response_data['message'] = 'User with this urn not found, or not possible get user info'

    return json_response(json.dumps(response_data), status=201)


@app.route('/send_messages', methods=['POST'], endpoint='send_messages')
@require_key
def send_messages():
    """
        if no old conversation, create new, else send into existing
    """
    api_is_working, linkedin, api_message = get_api(request)
    messages_sent = 0
    success = False
    if api_is_working:
        data = request.values
        message_body = data.get('message')
        max_connections = data.get('max_results', None)

        public_ids = data.get('public_ids', None)
        urn_ids = data.get('urn_ids', None)

        if public_ids and urn_ids:
            error = json.dumps({'error': 'pass only one - public_ids or urn_ids!'})
            return json_response(error, 400)

        try:
            if public_ids:
                public_ids = [x.strip() for x in public_ids.split(',')]
            elif urn_ids:
                urn_ids = [x.strip() for x in urn_ids.split(',')]
        except Exception:
            print_exc()
            error = json.dumps({'error': 'public_ids or urn_ids is invalid!'})
            return json_response(error, 400)

        if max_connections:
            max_connections = int(max_connections)

        send_message_interval = int(data.get('send_message_interval', 3))
        if not all([message_body]):
            error = json.dumps({'error': 'Missing some field/s (message)'})
            return json_response(error, 400)

        profile_connections = linkedin.get_profile_connections_raw(max_connections, only_urn=True)
        if profile_connections:
            for i, profile in enumerate(profile_connections):
                user_public_id = profile.get('publicIdentifier')
                user_urn_id = profile.get('entityUrn')

                if public_ids and (user_public_id not in public_ids):
                    continue
                elif urn_ids and (user_urn_id not in urn_ids):
                    continue

                conversation = linkedin.get_conversation_details(profile['entityUrn'])
                if conversation:
                    conversation_id = conversation['id']
                    message_sent = linkedin.send_message(conversation_id, message_body)
                    if message_sent:
                        print(profile['publicIdentifier'])
                        logger.info('Send message to {0} with {1} conversation'
                                    .format(profile['publicIdentifier'], conversation_id),
                                    {'extra': data.get('username'), 'section': 'message'})
                        messages_sent += 1

                else:
                    conversation_created = linkedin.create_conversation(profile['entityUrn'], message_body)
                    if conversation_created:
                        logger.info('Send message (new) to {0}'.format(profile['publicIdentifier']),
                                    {'extra': data.get('username'), 'section': 'message'})
                        messages_sent += 1

                if messages_sent and i + 1 != len(profile_connections):
                    sleep_timeout = randint(send_message_interval, send_message_interval + 2)
                    print('Wait...', sleep_timeout)
                    sleep(sleep_timeout)

    if messages_sent > 0:
        success = True

    response_data = {
        'api_is_working': api_is_working,
        'success': success,
        'messages_sent': messages_sent,
        'api_message': api_message
    }
    response_data = cronjob_generator(success, request, response_data)
    return json_response(json.dumps(response_data), status=201)


@app.route('/accept_invites', methods=['POST'], endpoint='accept_invites')
@require_key
def accept_invites():
    api_is_working, linkedin, api_message = get_api(request)
    accepted_invites = 0
    success = False

    if api_is_working:
        accepted_invites = linkedin.accept_invites()
        if accepted_invites <= 0:
            # handle error
            logger.info('Invites for {0} not found or not accepted! - {1}'
                        .format(request.values.get('username'), accepted_invites),
                        {'extra': request.values.get('username'), 'section': 'accept_invites'})
        else:
            logger.info('For {0} accepted {1} invites'.format(request.values.get('username'), accepted_invites),
                        {'extra': request.values.get('username'), 'section': 'accept_invites'})

    if accepted_invites > 0:
        success = True

    response_data = {
        'api_is_working': api_is_working,
        'success': success,
        'accept_invites': accepted_invites,
        'api_message': api_message
    }
    response_data = cronjob_generator(True, request, response_data)
    return json_response(json.dumps(response_data), status=201)


@app.route('/post_messages', methods=['POST'], endpoint='post_messages')
@require_key
def post_messages():
    """
    examples:
    https://www.linkedin.com/feed/update/urn:li:activity:6492467023828779008/
    https://www.linkedin.com/feed/update/urn:li:ugcPost:6494548936274116608/
    :return:
    """
    api_is_working, linkedin, api_message = get_api(request)
    success = False
    restli_id = None

    if api_is_working:
        data = request.values
        message_body = data.get('message')
        post_url = data.get('post_url')

        if not all([message_body, post_url]) or len(post_url.split(':')) < 2:
            error = json.dumps({'error': 'Missing some field/s (message_body, post_url)'})
            return json_response(error, 400)

        post_url = post_url.rstrip('/')
        post_id = post_url.split(':')[-1]
        format = post_url.split(':')[-2]

        if not post_id.isdigit():
            error = json.dumps({'error': 'post_url has wrong format!'})
            return json_response(error, 400)

        if format not in ['activity', 'ugcPost']:
            error = json.dumps({'error': 'post format not valid? {0}'.format(format)})
            return json_response(error, 400)

        # if format == 'activity': TODO: here in theory can be more formats...
        #     format = 'article'
        success, restli_id = linkedin.comment_on_post(format, post_id, message_body)

        if success:
            success = True
            logger.info('New post with {0} url from {1}'.format(data.get('username'), post_url),
                        {'extra': data.get('username'), 'section': 'post_messages'})
        else:
            logger.warning('Failed post with {0} url from {1}'.format(data.get('username'), post_url),
                           {'extra': data.get('username'), 'section': 'post_messages'})

    response_data = {
        'api_is_working': api_is_working,
        'success': success,
        'api_message': api_message,
        'restli_id': restli_id
    }
    response_data = cronjob_generator(success, request, response_data)
    return json_response(json.dumps(response_data), status=201)


@app.route('/delete_comment', methods=['POST'], endpoint='delete_comment')
@require_key
def delete_comment():
    """
    """
    api_is_working, linkedin, api_message = get_api(request)
    success = False

    if api_is_working:
        data = request.values
        ugc_post = data.get('ugc_post')

        if not all([ugc_post]) or len(ugc_post.split(',')) < 2:
            error = json.dumps({'error': 'Missing some field/s (ugc_post)'})
            return json_response(error, 400)

        success = linkedin.delete_comment(ugc_post)

    response_data = {'api_is_working': api_is_working, 'success': success, 'api_message': api_message}
    return json_response(json.dumps(response_data), status=201)


@app.route('/whoami', methods=['POST'], endpoint='whoami')
@require_key
def whoami():
    api_is_working, linkedin, api_message = get_api(request)
    success = False
    response_data = {}

    if api_is_working and linkedin:
        data = request.values
        max_connections = data.get('max_results', None)
        db = get_db()
        if max_connections:
            max_connections = int(max_connections)
            if max_connections <= 0:
                max_connections = None

        try:
            task_id = datetime.utcnow().strftime("%s") + '_' + str(uuid4()) + '_' + data.get('username')
            timestamp = datetime.utcnow()
            # We initialize taskid
            insert_or_replace_task(db, task_id, timestamp, data.get('username'), 'whoami', 0)
            # Run in background send invites
            executor.submit(get_user_connectons_in_background,
                            user=data.get('username'),
                            linkedin=linkedin,
                            task_id=task_id,
                            max_connections=max_connections,
                            timestamp=timestamp)
            response_data['task_id'] = task_id
            success = True
        except Exception:
            print_exc()
            pass

    response_data['api_is_working'] = api_is_working
    response_data['success'] = success
    response_data['message'] = api_message
    return json_response(json.dumps(response_data), status=201)


@app.route('/regions', methods=['POST'], endpoint='get_regions')
@require_key
def get_regions():
    regions = []
    api_is_working, linkedin, api_message = get_api(request)

    if api_is_working:
        regions = linkedin.get_regions()

    return json_response(json.dumps(regions), status=201)


@app.route('/logs', methods=['POST'], endpoint='get_logs')
@require_key
def get_logs():
    data = request.values
    task_id = data.get('task_id')
    tasks_data = {
        'state': None
    }

    if task_id:
        if not all([task_id]):
            error = json.dumps({'error': 'Missing some field/s (task_id)'})
            return json_response(error, 400)

        try:
            query = "SELECT * FROM tasks WHERE task_id = :task_id"
            tasks_data_raw = query_db(get_db(), query, dict(task_id=task_id), one=True)
            tasks_data_raw = dict(tasks_data_raw) or {}
            tasks_data.update(tasks_data_raw)
        except Exception as e:
            logging.error('Failed to get task_id %s' % str(e))
            pass

        if tasks_data:
            state = tasks_data.get('state', None)

            if state == 0:
                tasks_data['state'] = 'running'
                tasks_data['message'] = "Task is running"
            elif state == 1:
                tasks_data['state'] = 'success'
                tasks_data['message'] = "Task was finished successful"
            elif state == 2:
                tasks_data['state'] = 'failure'
                tasks_data['message'] = "Task was finished, but with error"
            elif state == 3:
                tasks_data['state'] = 'no_invites'
                tasks_data['message'] = "Task was finished, but invites not found!"
            else:
                tasks_data['state'] = 'unknow'
                tasks_data['message'] = "Task was deleted or not exist"
        else:
            tasks_data['state'] = 'unknow'
            tasks_data['message'] = "Task was deleted or not exist"

        if tasks_data.get('state') == 'success':
            # getting results
            if tasks_data.get('type') == 'whoami':
                query = "SELECT info FROM user WHERE email = :email"
                info = query_db(get_db(), query, dict(email=tasks_data.get('username')), one=True)
                if info:
                    info = dict(info)
                    if info and info.get('info'):
                        tasks_data['info'] = json.loads(info.get('info'))
                    else:
                        tasks_data['message'] = "Task was finished, but with error"
                        tasks_data['state'] = 'failure'
                else:
                    tasks_data['message'] = "Task was finished, but with error"
                    tasks_data['state'] = 'failure'

            elif tasks_data.get('type') == 'send_invites':
                query = "SELECT invites_sent FROM blacklists WHERE task_id = :task_id"
                info = query_db(get_db(), query, dict(task_id=task_id), one=True)
                if info:
                    info = dict(info)
                    if info and info.get('invites_sent'):
                        tasks_data['info'] = json.loads(info.get('invites_sent'))
                    else:
                        tasks_data['message'] = "Task was finished, but with error"
                        tasks_data['state'] = 'failure'
                else:
                    tasks_data['message'] = "Task was finished, but with error"
                    tasks_data['state'] = 'failure'

        tasks_data.update(tasks_data)
        return json_response(json.dumps(tasks_data), status=201)

    else:
        user = data.get('username')
        max_results = int(data.get('max_results', 200))
        order_keyword = data.get('order_keyword', 'DESC')

        if order_keyword not in ['ASC', 'DESC']:
            error = json.dumps({'error': 'Check your order param!'})
            return json_response(error, 400)

        if not all([user]):
            error = json.dumps({'error': 'Missing some field/s (username)'})
            return json_response(error, 400)

        log_data = []
        user_data = {
            'user': [],
            'codes': []
        }

        query = """
                SELECT *
                FROM blacklists
                WHERE username = :email
                ORDER BY timestamp {0} 
                LIMIT :limit;
                """.format(order_keyword)

        log_data_raw = query_db(get_db(), query,
                                dict(email=user, limit=max_results))

        query_user_data_raw = "SELECT email, date, login_date FROM user WHERE email = :email LIMIT :limit;"
        query_codes_data_raw = "SELECT email, headers FROM codes WHERE email = :email LIMIT :limit;"
        user_data_raw = query_db(get_db(), query_user_data_raw, dict(email=user, limit=max_results))
        codes_data_raw = query_db(get_db(), query_codes_data_raw, dict(email=user, limit=max_results))

        for row in log_data_raw:
            log_data.append(dict(row))

        for row in user_data_raw:
            user_data['user'].append(dict(row))

        for row in codes_data_raw:
            user_data['codes'].append({k: v for k, v in dict(row).items() if type(v) != bytes})
        return json_response(json.dumps({'log_data': log_data, 'user_data': user_data, 'user': user}), status=201)


@app.route('/check_job', methods=['POST'], endpoint='check_job')
@require_key
def check_job():
    data = request.values
    job_id = data.get('job_id')
    jobs_data = {'success': False}
    if not job_id:
        error = json.dumps({'error': 'Check your job id!'})
        return json_response(error, 400)

    if job_id and crontab:
        results = crontab.check_job(job_id)
        if len(results) > 1:
            logger.warning('Found multiple jobs for {0} job id!'.format(job_id),
                           {'extra': data.get('username'), 'section': 'crontab'})

        if len(results) > 0:
            jobs_data = results[0]
            jobs_data['success'] = True

    return json_response(json.dumps(jobs_data), status=201)


@app.route('/delete_job', methods=['POST'], endpoint='delete_job')
@require_key
def delete_job():
    data = request.values
    job_id = data.get('job_id')
    status = False
    if not job_id:
        error = json.dumps({'error': 'Check your job id!'})
        return json_response(error, 400)

    if job_id and crontab:
        with lock:
            status = bool(crontab.delete_job(job_id))

    return json_response(json.dumps({'job_deleted': status, 'success': status}), status=201)


@app.route('/delete_user', methods=['POST'], endpoint='delete_user')
@require_key
def delete_user():
    data = request.values
    user = data.get('username')
    removed_cronjobs = 0
    cron_error = None

    if not all([user]):
        error = json.dumps({'error': 'Missing some field/s (username)'})
        return json_response(error, 400)

    # Delete user from DB
    commit_db(get_db(), "DELETE FROM blacklists WHERE username = :email;", dict(email=user))
    commit_db(get_db(), "DELETE from user where email = :email;", dict(email=user))
    commit_db(get_db(), "DELETE from codes where email = :email;", dict(email=user))

    # Checking users
    log_status = query_db(get_db(),
                          "SELECT username FROM blacklists WHERE username = :email",
                          dict(email=user),
                          one=True)
    user_status = query_db(get_db(), "SELECT email FROM user WHERE email = :email", dict(email=user), one=True)
    code_status = query_db(get_db(), "SELECT email FROM codes WHERE email = :email", dict(email=user), one=True)

    if not all([log_status, user_status, code_status]):
        success = True
    else:
        success = False

    cronjobs = crontab.cron

    if cronjobs:
        try:
            jobs = cronjobs.find_comment(re.compile('_' + re.escape(user)))
            for job in jobs:
                cronjobs.remove(job)
                removed_cronjobs += 1

            with lock:
                cronjobs.write()
        except Exception as e:
            cron_error = str(e)
            pass

    response = {
        'success': success,
        'logs_not_exist': not log_status,
        'user_not_exist': not user_status,
        'user_codes_not_exist': not code_status,
        'cronjobs_removed': removed_cronjobs,
        'user': user
    }

    if cron_error:
        response['cron_error'] = cron_error

    return json_response(json.dumps(response), status=201)


@app.route('/tests_run', methods=['POST'], endpoint='run_tests')
@require_key
def run_tests():
    job_id = 'tests_' + datetime.utcnow().strftime("%s") + '_' + str(uuid4())
    log_file_path = os.path.join(APP_ROOT, 'logs', job_id + '.log')
    executor.submit(
        run_tests_in_background,
        APP_ROOT,
        log_file_path,
        names='{0}/tests/test_login.py {0}/tests/test_api*.py'.format(APP_ROOT)
    )
    return json_response(json.dumps({'job_id': job_id}), status=201)


@app.route('/tests_get', methods=['POST'], endpoint='tests_get')
@require_key
def tests_get():
    data = request.values
    job_id = data.get('job_id')
    if not job_id:
        error = json.dumps({'error': 'Check your job id!'})
        return json_response(error, 400)

    log_file_path = os.path.join(APP_ROOT, 'logs', job_id + '.log')
    if os.path.isfile(log_file_path):
        with open(log_file_path, 'r') as f:
            result = f.read()
            return json_response(json.dumps({'done': True,  'result': result}), status=201)

    else:
        return json_response(json.dumps({'done': False}), status=201)
