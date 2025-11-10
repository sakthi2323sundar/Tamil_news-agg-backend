from app.tamil_scraper import RSS_FEEDS, fetch_rss_feed, extract_entry_link, SOURCE_FETCH_POLICY

for source, urls in RSS_FEEDS.items():
    total=0
    print(f"\nSource: {source}")
    entries=[]
    for u in urls:
        e=fetch_rss_feed(u)
        print(f"  URL: {u} -> {len(e)} entries")
        if e and not entries:
            entries=e
    seen=set()
    kept=0
    for i,entry in enumerate(entries[:10]):
        link=extract_entry_link(entry)
        if link and link not in seen:
            kept+=1
            seen.add(link)
        print(f"   {i+1:02d}. link={bool(link)} title={(entry.get('title') or '')[:60]}")
    print(f"  dedup kept among first 10: {kept}")
