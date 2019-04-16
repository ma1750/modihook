import asyncio
from datetime import datetime, timedelta, timezone
from aiohttp import ClientSession

from config import Config


IGNORE_MODIFY = 1800
REFRESH_INTERVAL = 300

loop = asyncio.get_event_loop()
session = ClientSession()
config = Config(__file__, 'config.json')
webhooks = config.get('webhooks')
urls = config.get('urls')

last_modified = {}
jst = timezone(timedelta(hours=+9), 'JST')

async def head(url):
    try:
        async with session.head(url) as res:
            modified = res.headers.get('Last-Modified')
            if modified:
                modified_time = datetime.strptime(modified, '%a, %d %b %Y %H:%M:%S GMT').replace(tzinfo=timezone.utc)
                print(f'{modified_time.astimezone(jst).strftime("%Y/%m/%d %H:%M")} : {url}')
                return modified_time
            else:
                print(f'No Last-Modified found for {url}')
                return None
    except:
        print(f'Failed to get {url}')

async def handle_url(url):
    res = await head(url)
    if res:
        if last_modified.get(url):
            delta = res - last_modified[url]
            if delta.total_seconds() > IGNORE_MODIFY:
                await asyncio.wait([post_webhook(url, res, hook) for hook in webhooks])
        
        last_modified[url] = res

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
        await asyncio.wait([handle_url(url) for url in urls])

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
