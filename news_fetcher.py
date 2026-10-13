#!/usr/bin/env python3
"""Daily Chinese AI digest: standard-library-only local server."""
import concurrent.futures
import datetime as dt
import email.utils
import html
import json
import os
import pathlib
import re
import socket
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
import xml.etree.ElementTree as ET
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT = pathlib.Path(__file__).resolve().parent
CACHE = ROOT / 'cache.json'
TZ = dt.timezone(dt.timedelta(hours=8))
HEADERS = {'User-Agent':'Mozilla/5.0 (compatible; AIDailyChinese/1.0)'}
QUERIES = {
 'news': '(人工智能 OR 生成式AI OR 大模型) when:2d',
 'fashion': '(AI服装设计 OR AI时尚设计 OR 人工智能服装) when:7d',
 'education': '(人工智能 教育 青少年 OR AI儿童教育 OR AI学习工具) when:7d',
 'future': '(人工智能 趋势 OR AI产业 发展 OR AI未来) when:7d',
 'tools': '(AI工具 新功能 OR AI应用 教程) when:7d',
}
LABELS = {'news':'AI热点新闻','fashion':'AI × 服装设计','education':'AI × 儿童青少年教育','future':'未来趋势观察','tools':'工具与应用'}
LOCK = threading.Lock()


def fetch_one(key, query):
    # Try Chinese Bing News first (commonly reachable without Google), then Google News.
    urls = [
        'https://www.bing.com/news/search?' + urllib.parse.urlencode({'q':query.replace(' when:2d','').replace(' when:7d',''),'format':'rss','setlang':'zh-Hans','cc':'CN'}),
        'https://news.google.com/rss/search?' + urllib.parse.urlencode({'q':query,'hl':'zh-CN','gl':'CN','ceid':'CN:zh-Hans'})
    ]
    last_error = None
    for url in urls:
        try:
            request = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(request, timeout=9) as response:
                raw = response.read(1024*1024)
            root = ET.fromstring(raw)
            rows = []
            for item in root.findall('./channel/item')[:16]:
                title = html.unescape((item.findtext('title') or '').strip())
                link = (item.findtext('link') or '').strip()
                source = html.unescape((item.findtext('source') or '').strip())
                # Bing exposes the provider in News namespace.
                if not source:
                    for child in item:
                        if child.tag.endswith('Source') and child.text:
                            source = child.text.strip()
                            break
                stamp = (item.findtext('pubDate') or '').strip()
                if not title or not link: continue
                if source and title.endswith(' - '+source): title = title[:-(len(source)+3)]
                try:
                    published = email.utils.parsedate_to_datetime(stamp).astimezone(TZ).isoformat(timespec='minutes')
                except Exception:
                    published = ''
                rows.append({'title':title, 'url':link, 'source':source or '新闻来源', 'published':published,'category':key})
            if rows: return rows[:9]
        except Exception as exc:
            last_error = exc
    raise RuntimeError('No accessible news RSS provider: ' + repr(last_error))


def load_cache():
    try:
        return json.loads(CACHE.read_text(encoding='utf-8'))
    except Exception:
        return None


def refresh(force=False):
    with LOCK:
        cached = load_cache()
        today = dt.datetime.now(TZ).date().isoformat()
        if cached and not force and cached.get('date') == today:
            return cached
        items = dict((key, []) for key in QUERIES)
        failed = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            futures = {pool.submit(fetch_one, k, q):k for k,q in QUERIES.items()}
            for f in concurrent.futures.as_completed(futures):
                key = futures[f]
                try: items[key] = f.result()
                except Exception as exc:
                    failed.append(key)
                    print('Feed failed:', key, repr(exc), flush=True)
                    if cached: items[key] = cached.get('items', {}).get(key, [])
        fresh_count = sum(bool(items[k]) for k in items if k not in failed)
        result = {
          'date': today if fresh_count else (cached or {}).get('date', today),
          'checked_at': dt.datetime.now(TZ).isoformat(timespec='minutes'),
          'items':items,
          'labels':LABELS,
          'fresh':bool(fresh_count),
          'stale_categories':failed,
          'message': '已获取资讯' if fresh_count else '本次联网获取失败；显示上次缓存（如有），请检查网络后重试。',
        }
        if fresh_count: CACHE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        return result


class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(ROOT),**kwargs)
    def do_GET(self):
        p = urllib.parse.urlsplit(self.path)
        if p.path == '/api/news':
            try:
                data = refresh(force=urllib.parse.parse_qs(p.query).get('refresh')==['1'])
                body = json.dumps(data, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type','application/json; charset=utf-8')
                self.send_header('Cache-Control','no-store')
                self.send_header('Content-Length',str(len(body)))
                self.end_headers(); self.wfile.write(body)
            except Exception as e:
                body = json.dumps({'error':str(e)},ensure_ascii=False).encode('utf-8')
                self.send_response(500);self.send_header('Content-Type','application/json; charset=utf-8');self.end_headers();self.wfile.write(body)
        elif p.path in ('/','/index.html','/favicon.svg'):
            self.path = '/index.html' if p.path=='/' else p.path
            return super().do_GET()
        else:
            self.send_error(404)
    def log_message(self,fmt,*args):
        if not self.path.startswith('/api/'): return
        print(fmt % args, flush=True)


def main():
    server = None
    for port in range(8765,8790):
        try:
            server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
            break
        except OSError: pass
    if server is None:
        print('No free port.');return
    url=f'http://127.0.0.1:{server.server_port}/'
    print('AI 中文日报已启动:',url,flush=True)
    threading.Timer(1.2,lambda:webbrowser.open(url)).start()
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
