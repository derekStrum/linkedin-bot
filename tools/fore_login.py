import requests
from dotenv import load_dotenv
from os.path import join, dirname
from os import getenv
from time import sleep
from random import choice

dotenv_path = join(dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)
url = getenv("LINKEDIN_SEVER_ADDRESS") + '/login'

with open('output_proxy.txt') as f:
    proxies = f.read().splitlines()

for proxy in proxies:
    try:
        with requests.Session() as client:
            client.proxies = {
                'http': proxy,
                'https': proxy
            }

            client.get('https://www.linkedin.com/uas/login?trk=guest_homepage-basic_nav-header-signin', timeout=2)
    except Exception as e:
        print(str(e))
        pass
        continue

    proxy = choice(proxies)
    resp = requests.post(url,
                         headers={'x-api-key': getenv("API_KEY")},
                         data={
                             'username': 'destinyperez94@aol.com',
                             'password': 'cG9A2rjOv',
                             'proxy': proxy,
                             'auto_fill_code': 'true'
                         })

    try:
        print(proxy)
        print(resp.json())
        if resp.json() and resp.json().get('api_is_working') == 'need_key':
            print(resp.json().get('api_is_working'))
            break
        elif resp.json() and resp.json().get('api_message') == 'Successfully logged-in with filling pin code!':
            print(resp.json().get('api_is_working'))
            break

    except Exception as e:
        print(str(e))
