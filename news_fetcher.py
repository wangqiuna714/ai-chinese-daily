import os, json, re, time, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone, timedelta
import xml.etree.ElementTree as ET

OUT='news.json'
BEIJING=timezone(timedelta(hours=8))
FEEDS=[
 ('OpenAI','https://openai.com/news/rss.xml','official'),
 ('Anthropic','https://www.anthropic.com/news/rss.xml','official'),
 ('Google AI Blog','https://blog.research.google/feeds/posts/default?alt=rss','official'),
 ('Google DeepMind','https://deepmind.google/blog/rss.xml','official'),
 ('NVIDIA Blog','https://blogs.nvidia.com/feed/','official'),
 ('Hugging Face','https://huggingface.co/blog/feed.xml','official'),
 ('GitHub Blog','https://github.blog/feed/','official'),
 ('TechCrunch AI','https://techcrunch.com/category/artificial-intelligence/feed/','media'),
 ('MIT Technology Review','https://www.technologyreview.com/feed/','media'),
 ('The Verge AI','https://www.theverge.com/rss/ai-artificial-intelligence/index.xml','media'),
 ('arXiv AI','https://export.arxiv.org/rss/cs.AI','research'),
 ('arXiv Robotics','https://export.arxiv.org/rss/cs.RO','research'),
]
CATEGORIES={
 'AI Agent':[r'\bagents?\b',r'agentic',r'computer use',r'workflow automation',r'agent framework',r'自主代理',r'智能体'],
 'AI Coding':[r'coding',r'code generation',r'programming agent',r'developer tool',r'github copilot',r'code assistant',r'编程',r'代码生成'],
 '端侧 AI 与硬件':[r'edge ai',r'on-device',r'端侧',r'edge model',r'phone ai',r'wearable',r'chip',r'gpu',r'processor',r'robotics hardware',r'AI hardware',r'智能眼镜',r'硬件'],
 '多模态与视频生成':[r'multimodal',r'video generation',r'image generation',r'text-to-video',r'audio generation',r'vision-language',r'world model',r'多模态',r'视频生成'],
 'AI 具身智能':[r'embodied',r'humanoid',r'robot foundation model',r'robot learning',r'physical ai',r'具身智能',r'人形机器人',r'机器人操作'],
}

def clean(s):
    s=re.sub(r'<[^>]+>',' ',s or '')
    s=re.sub(r'&nbsp;',' ',s)
    return re.sub(r'\s+',' ',s).strip()

def get_text(node, names):
    # Match both ordinary XML tags and namespaced tags by local name.
    wanted={n.split('}')[-1].split(':')[-1].lower() for n in names}
    for el in node.iter():
        local=el.tag.split('}')[-1].split(':')[-1].lower() if isinstance(el.tag,str) else ''
        if local in wanted and el.text and el.text.strip(): return clean(el.text)
    return ''

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'ZhixinAIDaily/1.0 (RSS reader; contact: site owner)'})
    with urllib.request.urlopen(req,timeout=20) as r: return r.read()

def parse_feed(name,url,kind):
    try:
        raw=fetch(url); root=ET.fromstring(raw); items=[]
        for node in root.findall('.//item')[:40]:
            title=get_text(node,['title']); link=get_text(node,['link']); desc=get_text(node,['description','content:encoded']); pub=get_text(node,['pubDate','published','updated'])
            if title and link: items.append({'title_en':title,'url':link,'description_en':desc[:1400],'published_raw':pub,'source':name,'source_type':kind})
        if not items:
            ns={'a':'http://www.w3.org/2005/Atom','content':'http://purl.org/rss/1.0/modules/content/'}
            for node in root.findall('.//a:entry',ns)[:40]:
                title=get_text(node,['{http://www.w3.org/2005/Atom}title']); link=''
                for le in node.findall('{http://www.w3.org/2005/Atom}link'):
                    href=le.attrib.get('href','')
                    if href and le.attrib.get('rel','alternate')=='alternate': link=href; break
                desc=get_text(node,['{http://www.w3.org/2005/Atom}summary','{http://www.w3.org/2005/Atom}content'])
                pub=get_text(node,['{http://www.w3.org/2005/Atom}published','{http://www.w3.org/2005/Atom}updated'])
                if title and link: items.append({'title_en':title,'url':link,'description_en':desc[:1400],'published_raw':pub,'source':name,'source_type':kind})
        print(f'{name}: {len(items)} items')
        return items
    except Exception as e:
        print(f'Feed failed {name}: {e}'); return []

def parse_date(s):
    if not s:return ''
    try:
        from email.utils import parsedate_to_datetime
        dt=parsedate_to_datetime(s)
        if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(BEIJING).isoformat()
    except Exception:
        try:
            dt=datetime.fromisoformat(s.replace('Z','+00:00'))
            if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(BEIJING).isoformat()
        except Exception:return ''

def category_for(item):
    text=(item.get('title_en','')+' '+item.get('description_en','')).lower()
    for cat, pats in CATEGORIES.items():
        if any(re.search(p,text,re.I) for p in pats): return cat
    return '行业与研究'

def gemini_json(items, api_key):
    if not api_key: raise RuntimeError('Missing GEMINI_API_KEY')
    endpoint='https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key='+urllib.parse.quote(api_key)
    prompt='你是严谨的中文AI科技编辑。对输入的英文AI资讯逐条做中文编辑。必须只根据输入内容，不得补造事实；无法确认的影响写“需进一步验证”。每条输出字段：id,title_zh,summary_zh,why_it_matters。title_zh为自然中文标题；summary_zh用中文概括2句，约60-110字；why_it_matters用中文解释值得关注的原因，1句，尽量具体。若内容与AI关联弱，可保守概括。另输出daily_summary_zh（约150-220字的当日总结，不能捏造跨条目因果）和takeaways_zh（3条中文观察）。严格返回JSON对象，结构必须是 {\"items\":[{\"id\":\"0\",\"title_zh\":\"...\",\"summary_zh\":\"...\",\"why_it_matters\":\"...\"}],\"daily_summary_zh\":\"...\",\"takeaways_zh\":[\"...\",\"...\",\"...\"]}，不要Markdown。输入：'+json.dumps(items,ensure_ascii=False)
    body={'contents':[{'parts':[{'text':prompt}]}],'generationConfig':{'responseMimeType':'application/json','temperature':0.2}}
    req=urllib.request.Request(endpoint,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(req,timeout=90) as r: data=json.loads(r.read())
    txt=data['candidates'][0]['content']['parts'][0]['text']
    return json.loads(txt)

def main():
    all_items=[]
    for name,url,kind in FEEDS: all_items.extend(parse_feed(name,url,kind))
    seen=set(); unique=[]
    for x in all_items:
        key=x['url'].split('?')[0].rstrip('/')
        if key in seen: continue
        seen.add(key); x['category']=category_for(x); x['published_at']=parse_date(x.pop('published_raw',''))
        unique.append(x)
    cutoff=datetime.now(timezone.utc)-timedelta(days=10)
    recent=[]
    for x in unique:
        try:
            d=datetime.fromisoformat(x['published_at'])
            if d.astimezone(timezone.utc)>=cutoff: recent.append(x)
        except Exception: recent.append(x)
    recent.sort(key=lambda x:x.get('published_at',''),reverse=True)
    # Balanced selection: prioritize recency while retaining representation across focus areas.
    selected=[]; used=set(); counts={}
    for x in recent:
        c=x['category']
        if counts.get(c,0)<5 and len(selected)<28:
            selected.append(x); counts[c]=counts.get(c,0)+1; used.add(x['url'])
    if len(selected)<12:
        for x in recent:
            if x['url'] not in used:
                selected.append(x)
                if len(selected)>=20:break
    selected=selected[:28]
    brief_inputs=[{'id':str(i),'title':x['title_en'],'description':x.get('description_en','')[:900],'source':x['source'],'category':x['category']} for i,x in enumerate(selected)]
    try:
        result=gemini_json(brief_inputs,os.getenv('GEMINI_API_KEY',''))
        edited={str(x.get('id')):x for x in result.get('items',[]) if isinstance(x,dict)}
    except Exception as e:
        print('Chinese editorial generation failed:',e)
        result={'daily_summary_zh':'今日中文总结合成暂未成功。以下保留可追溯的原始资讯，请通过原文核对内容。','takeaways_zh':['优先核对官方公告、论文或代码仓库。','区分已发布功能、研究演示和社区推测。','关注真实应用效果、成本、速度与可靠性。']}; edited={}
    final=[]
    for i,x in enumerate(selected):
        e=edited.get(str(i),{})
        final.append({'title_en':x['title_en'],'title_zh':e.get('title_zh',x['title_en']),'summary_zh':e.get('summary_zh','中文摘要生成失败，请阅读原文。'),'why_it_matters':e.get('why_it_matters','请以原文为准，进一步核对其实际能力与影响。'),'url':x['url'],'source':x['source'],'source_type':x['source_type'],'category':x['category'],'published_at':x.get('published_at','')})
    output={'updated_at':datetime.now(BEIJING).isoformat(),'daily_summary_zh':result.get('daily_summary_zh',''),'takeaways_zh':result.get('takeaways_zh',[]),'news':final,'source_count':len(FEEDS),'note':'自动汇总仅作信息参考；请查看原文核验。'}
    with open(OUT,'w',encoding='utf-8') as f: json.dump(output,f,ensure_ascii=False,indent=2)
    print(f'Wrote {OUT}: {len(final)} stories')

if __name__=='__main__': main()
