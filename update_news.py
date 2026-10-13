"""Fetch Chinese RSS news and publish a static JSON snapshot."""
import json
from pathlib import Path
import news_fetcher

output = Path(__file__).with_name('news.json')
result = news_fetcher.refresh(force=True)
count = sum(len(v) for v in result.get('items', {}).values())
if count == 0:
    print('No news available; preserve last published data.')
else:
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Published', count, 'articles')
