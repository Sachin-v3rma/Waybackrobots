#!/usr/bin/python3
""" Coded by Sachin verma with <3 """

import pathlib
import asyncio
import re
import sys
from typing import IO
import urllib.error
import urllib.parse
import aiofiles
import aiohttp
from aiohttp import ClientSession
import argparse
import time

start = time.perf_counter()


class col:
    magenta = '\033[95m'
    cyan = '\033[96m'
    green = '\033[92m'
    red = '\033[91m'
    reset = '\033[0m'

async def fetch_robots_url(domain):
    timestamp = f"https://web.archive.org/cdx/search/cdx/?url={domain}/robots.txt&output=json&fl=timestamp,original&filter=statuscode:200&collapse=digest"
    async with aiohttp.ClientSession() as session:
        resp=await session.request(method="GET",url=timestamp)
        rhtml = await resp.json()
        rhtml.pop(0)
        return rhtml

async def robots_url(domain):
    rhtml = await fetch_robots_url(domain)
    urls=[]
    for i in range(len(rhtml)):
        urls.append(f"https://web.archive.org/web/{rhtml[i][0]}/{rhtml[i][1]}")
    return urls

async def fetch_html(url: str, session: ClientSession, **kwargs) -> str:
    resp = await session.request(method="GET", url=url, **kwargs)
    resp.raise_for_status()
    html = await resp.text()
    return html


async def parse(url: str, session: ClientSession, **kwargs) -> set:
    found = set()
    try:
        html = await fetch_html(url=url, session=session, **kwargs)
    except (ConnectionRefusedError, aiohttp.client_exceptions.ClientConnectorError):
        pass
        return found
    else:
        if 'Disallow:' in html:
            for link in re.findall('/.*',html):
                found.add(link)
        return found


async def output(file: IO, url: str, **kwargs) -> None:
    res = await parse(url=url, **kwargs)
    if not res:
        return None
    async with aiofiles.open(file, "a") as f:
        for p in res:
            await f.write(f"{p}\n")
        print(f"{col.green}Fetched paths from : {col.cyan}{url}{col.reset}")


async def bulk_crawl_and_write(file: IO, domain: set,threads, **kwargs) -> None:
    connector = aiohttp.TCPConnector(limit_per_host=threads)
    async with ClientSession(connector=connector) as session:
        tasks = []
        print(f"{col.magenta}[+]{col.green} Searching for Wayback URLs and Timestamp : {col.cyan}{domain}{col.reset}\n")
        urls = await robots_url(domain)
        print(f"{col.magenta}[+]{col.green} Found {col.cyan}{len(urls)}{col.reset}{col.green} URLs{col.reset}\n")
        for url in urls:
            tasks.append(
                output(file=file, url=url, session=session, **kwargs)
            )
        await asyncio.gather(*tasks)  # see also: return_exceptions=True


if __name__ == "__main__":
    #Timer start
    tic = time.perf_counter()

    #Arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('url', help='domain or url')
    parser.add_argument('-o', '--output', help='output directory', dest='output')
    parser.add_argument('-t', '--threads', help='number of threads', dest='threads', type=int, default=10)
    args = parser.parse_args()

    domain = args.url
    if args.output:
        outpath = args.output
    else:
        here = pathlib.Path(__file__).parent
        outpath = here.joinpath(f"robo_{domain}.txt")
    threads = args.threads

    try:
        asyncio.run(bulk_crawl_and_write(outpath,domain,threads))
        toc = time.perf_counter()
        print(f"{col.green}\nFinished in {col.cyan}{toc - tic:0.4f}{col.green} seconds{col.reset}")
    except KeyboardInterrupt:
        print(f'\n{col.magenta}[-]{col.red} Exiting{col.reset}')
        sys.exit()
    except IndexError:
        print(f'{col.magenta}[-]{col.red} No URLs and timestamps found{col.reset}')
        sys.exit()
    



