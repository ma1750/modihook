import asyncio
from datetime import datetime, timedelta, timezone
from aiohttp import ClientSession

from config import Config


loop = asyncio.get_event_loop()
session = ClientSession()
webhooks = Config(__file__, 'webhooks.json').get('webhooks')
urls = Config(__file__, 'urls.json').get('urls')

last_modified = {}
jst = timezone(timedelta(hours=+9), 'JST')

async def head(url):
    async with session.head(url) as res:
        modified = res.headers.get('Last-Modified')
        if modified:
            modified_time = datetime.strptime(modified, '%a, %d %b %Y %H:%M:%S GMT').replace(tzinfo=timezone.utc)
            print(f'{modified_time.astimezone(jst).strftime("%Y/%m/%d %H:%M")} : {url}')
            return modified_time
        else:
            print(f'{url} {res.status}: {res.reason}')
            return None

async def handle_url(url):
    res = await head(url)
    if res:
        if last_modified[url] and last_modified[url] < res:
            await asyncio.wait([post_webhook(url, res, hook) for hook in webhooks])
        else:
            last_modified[url] = res

async def post_webhook(url, res, hook):
    payload = {
        'content': f'Modify detected!\n{res.astimezone(jst).strftime("%Y/%m/%d %H:%M")}\n{url}'
    }
    async with session.post(hook, json=payload) as resp:
        if not resp.status == 200:
            print(f'Failed to POST {hook}')

async def run():
    await asyncio.wait([handle_url(url) for url in urls])
    await asyncio.sleep(300)
    await run()

if __name__ == '__main__':
    loop.create_task(run())
    print('Started')
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.stop()
        print('Stopped')
    
    loop.close()
