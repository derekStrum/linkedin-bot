import re
import json
from datetime import datetime

def get_id_from_urn(urn):
    """
    Return the ID of a given Linkedin URN.

    Example: urn:li:fs_miniProfile:<id>
    """
    return urn.split(":")[3]


def get_requests_proxies(proxy):
    if proxy[2]:
        proxy = proxy[2][0] + ':' + proxy[2][1] + '@' + proxy[1]
    else:
        proxy = proxy[1]

    proxies = {'http': 'http://' + proxy, 'https': 'https://' +proxy}
    return proxies


def smart_proxy_parser(proxy):
    proxy = proxy.strip()
    type = 'http'

    if proxy.startswith('http://'):
        type = 'http'
        proxy = proxy[7:]
    elif proxy.startswith('https://'):
        type = 'https'
        proxy = proxy[8:]
    elif proxy.startswith('socks4://'):
        type = 'socks4'
        proxy = proxy[9:]
    elif proxy.startswith('socks5://'):
        type = 'socks5'
        proxy = proxy[9:]

    ip = None
    port = None
    user = None
    password = None

    # match 1
    pattern_1 = re.compile("^(\d+\.\d+\.\d+\.\d+):(\d+):(.*)?:(.*)$")
    matches_1 = pattern_1.match(proxy)

    # match 2
    pattern_2 = re.compile("^(\d+\.\d+\.\d+\.\d+):(\d+)$")
    matches_2 = pattern_2.match(proxy)

    parsed_proxy = None

    if matches_1:
        ip = matches_1.group(1)
        port = matches_1.group(2)
        user = matches_1.group(3)
        password = matches_1.group(4)
    elif matches_2:
        ip = matches_2.group(1)
        port = matches_2.group(2)
        user = None
        password = None

    if ip and port:
        parsed_proxy = ip + ':' + port

    if user and password:
        proxy_auth = [user, password]
    else:
        proxy_auth = None

    if parsed_proxy:
        return type, parsed_proxy, proxy_auth
    else:
        return None


def utc_mktime():
    d = datetime.utcnow()
    epoch = datetime(1970,1,1)
    t = (d - epoch).total_seconds()
    return t


def parse_mini_profile(base_info):
    base_info = {k: v for k, v in base_info.items() if k in
                 [
                     'firstName',
                     'lastName',
                     'occupation',
                     'publicIdentifier',
                     'picture',
                     'entityUrn'
                 ]}
    pictures = base_info.get('picture', {}).get('com.linkedin.common.VectorImage', {})
    root_url = base_info.get('picture', {}).get('com.linkedin.common.VectorImage', {}).get('rootUrl')
    base_info['picture'] = []
    base_info['urn'] = get_id_from_urn(base_info.get('entityUrn'))

    for picture in pictures.get('artifacts', []):
        base_info['picture'].append(
            {
                'url': root_url + picture['fileIdentifyingUrlPathSegment'],
                'dimensions': str(picture['width']) + 'x' + str(picture['height']),
                'expiresAt': picture['expiresAt']
            }
        )

    return base_info


def get_default_regions(file='regions.json'):
    regions = []
    try:
        with open(file) as f:
            regions = json.load(f)
    except Exception:
        pass

    return regions
