import requests, feedparser
from pprint import pprint

URLS=[
  'https://tamil.news18.com/commonfeeds/v1/tam/rss/live-updates.xml',
  'https://tamil.news18.com/commonfeeds/v1/tam/rss/coimbatore-district.xml'
]

headers={'User-Agent':'Mozilla/5.0'}
for url in URLS:
    print('\nURL:', url)
    r=requests.get(url, timeout=20, headers=headers)
    print('HTTP:', r.status_code, r.headers.get('Content-Type',''))
    feed=feedparser.parse(r.content)
    print('entries:', len(feed.entries))
    if feed.entries:
        e=feed.entries[0]
        keys=sorted(list(e.keys()))
        print('first entry keys:', keys)
        print('title:', e.get('title','')[:120])
        print('link:', e.get('link'))
        print('links:', e.get('links'))
        print('id:', e.get('id'))
        print('guid:', e.get('guid'))
        print('published:', e.get('published'))
        print('summary:', (e.get('summary') or '')[:140])
