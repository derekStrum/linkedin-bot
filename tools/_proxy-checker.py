#!/usr/bin/env python3
import asyncio
from aiohttp import ClientSession, TCPConnector
from aiomultiprocess import Pool
from itertools import repeat
import argparse
from traceback import print_exc

async def get(test_url, url, timeout):
    async with ClientSession(connector=TCPConnector(ssl=False, force_close=True), raise_for_status=True, conn_timeout=timeout, read_timeout=timeout*2) as client:
        try:
            response = await client.get(test_url, proxy='http://' + url)
            if response.status == 200:
                return url
        except:
            pass

async def main(test_url, proxy_list, timeout, output):
    async with Pool(processes=8, childconcurrency=1000) as pool:
        item = zip(repeat(test_url), proxy_list, repeat(timeout))
        result = await pool.starmap(get, item)
        result = list(filter(None.__ne__, result))
        with open(output, 'w') as f:
            for item in result:
                f.write("%s\n" % item)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('test_url')
    parser.add_argument('file', type=argparse.FileType('r', encoding='UTF-8'))
    parser.add_argument('--timeout', default=10)
    parser.add_argument('--output', default='output_proxy.txt')
    args = parser.parse_args()
    proxy_list = args.file.read().splitlines()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(args.test_url, proxy_list, args.timeout, args.output))
    loop.close()

