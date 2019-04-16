import asyncio
import difflib
import re
from datetime import datetime, timedelta, timezone

from aiohttp import ClientSession
from bs4 import BeautifulSoup

from config import Config

IGNORE_MODIFY = 1800
REFRESH_INTERVAL = 300

loop = asyncio.get_event_loop()
session = ClientSession()
config = Config(__file__, 'config.json')
webhooks = config.get('webhooks')
urls = config.get('urls')

last_modified = {}
previous_text = {}
jst = timezone(timedelta(hours=+9), 'JST')

async def fetch(url):
    try:
        async with session.get(url) as res:
            modified = res.headers.get('Last-Modified')
            if modified:
                modified_time = datetime.strptime(modified, '%a, %d %b %Y %H:%M:%S GMT').replace(tzinfo=timezone.utc)
                print(f'{modified_time.astimezone(jst).strftime("%Y/%m/%d %H:%M")} : {url}')
                return modified_time
            else:
                print(f'"Last-Modified" element does not exsist for {url}')
                soup = BeautifulSoup(await res.text(), 'html.parser')
                return soup.text
    except:
        print(f'Failed to get {url}')

async def diff(url):
    res = await fetch(url)
    if res:
        if isinstance(res, datetime):
            if last_modified.get(url):
                delta = res - last_modified[url]
                if delta.total_seconds() > IGNORE_MODIFY:
                    await asyncio.wait([post_webhook(url, res, hook) for hook in webhooks])
            
            last_modified[url] = res
        elif isinstance(res, str):
            res = re.sub(r' +', ' ', (re.sub(r'\n+', '\n', res)))
            changed = difflib.ndiff(previous_text[url].splitlines(keepends=True), res.splitlines(keepends=True))
            for line in changed:
                if ' ' not in line[0]:
                    await asyncio.wait([post_webhook(url, datetime.now(), hook) for hook in webhooks])
                    break
                    
            previous_text[url] = res

async def post_webhook(url, res, hook):
    payload = {
        'content': f'Modify detected!\n{res.astimezone(jst).strftime("%Y/%m/%d %H:%M")}\n{url}'
    }
    async with session.post(hook, json=payload) as resp:
        if not resp.status == 200:
            print(f'Failed to POST {hook}')

async def refresh():
    if urls:
        print(f'\nChecking: {datetime.now().strftime("%Y/%m/%d %H:%M")}')
        await asyncio.wait([diff(url) for url in urls])

async def schedule():
    await asyncio.sleep(REFRESH_INTERVAL)
    asyncio.ensure_future(schedule())
    await refresh()

async def run():
    asyncio.ensure_future(schedule())
    await refresh()


if __name__ == '__main__':
    # loop.set_debug(True)
    loop.create_task(run())
    print('Started')
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.stop()
        print('Stopped')
    
    loop.close()
