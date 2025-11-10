from collections import Counter
from app.database import SessionLocal
from app.models import News

session = SessionLocal()
try:
    rows = session.query(News.source, News.url).all()
    c = Counter(src for src, _ in rows)
    print('Total rows:', len(rows))
    for src, n in c.most_common():
        print(f'{src}: {n}')
    # Show a few sample URLs per source
    for src in list(c.keys())[:5]:
        urls = [u for s,u in rows if s==src][:5]
        print(f'Examples for {src}:')
        for u in urls:
            print('  ', u)
finally:
    session.close()
