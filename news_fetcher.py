import json
import re
import time
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

OUT = "news.json"
BEIJING = timezone(timedelta(hours=8))

FEEDS = [
    ("OpenAI", "https://openai.com/news/rss.xml", "official"),
    ("Google AI Blog", "https://blog.research.google/feeds/posts/default?alt=rss", "official"),
    ("Google DeepMind", "https://deepmind.google/blog/rss.xml", "official"),
    ("NVIDIA Blog", "https://blogs.nvidia.com/feed/", "official"),
    ("Hugging Face", "https://huggingface.co/blog/feed.xml", "official"),
    ("GitHub Blog", "https://github.blog/feed/", "official"),
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/", "media"),
    ("MIT Technology Review", "https://www.technologyreview.com/feed/", "media"),
    ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "media"),
    ("arXiv AI", "https://export.arxiv.org/rss/cs.AI", "research"),
    ("arXiv Robotics", "https://export.arxiv.org/rss/cs.RO", "research"),
    ("Hacker News", "https://hnrss.org/frontpage", "community"),
]

CATEGORIES = {
    "AI Agent": [r"\bagents?\b", r"agentic", r"computer use", r"workflow automation", r"agent framework", r"智能体"],
    "AI Coding": [r"coding", r"code generation", r"programming agent", r"developer tool", r"github copilot", r"code assistant", r"编程", r"代码生成"],
    "端侧 AI 与硬件": [r"edge ai", r"on-device", r"端侧", r"edge model", r"phone ai", r"wearable", r"\bchip\b", r"\bgpu\b", r"processor", r"robotics hardware", r"AI hardware", r"智能眼镜", r"硬件"],
    "多模态与视频生成": [r"multimodal", r"video generation", r"image generation", r"text-to-video", r"audio generation", r"vision-language", r"world model", r"多模态", r"视频生成"],
    "AI 具身智能": [r"embodied", r"humanoid", r"robot foundation model", r"robot learning", r"physical ai", r"robotics", r"robot", r"具身智能", r"人形机器人", r"机器人操作"],
}

WHY = {
    "AI Agent": "关注它能否可靠调用工具并完成多步骤任务，以及是否有真实应用证据。",
    "AI Coding": "关注它对开发效率、代码质量、测试能力和软件开发流程的实际影响。",
    "端侧 AI 与硬件": "关注本地运行能力，以及延迟、隐私、能耗和硬件成本之间的取舍。",
    "多模态与视频生成": "关注图像、视频和声音处理能力，以及生成质量、可控性与应用成本。",
    "AI 具身智能": "关注系统在真实物理环境中的感知、规划和动作能力，而不只看演示视频。",
    "行业与研究": "关注结论是否有官方公告、原始论文或可复现技术材料支持。",
}


def clean(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = re.sub(r"&nbsp;", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def get_text(node, names):
    wanted = {n.split("}")[-1].split(":")[-1].lower() for n in names}
    for el in node.iter():
        local = el.tag.split("}")[-1].split(":")[-1].lower() if isinstance(el.tag, str) else ""
        if local in wanted and el.text and el.text.strip():
            return clean(el.text)
    return ""


def fetch(url, timeout=18):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; ZhixinAIDaily/2.1)"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def parse_feed(name, url, kind):
    try:
        root = ET.fromstring(fetch(url))
        items = []
        for node in root.findall(".//item")[:35]:
            title = get_text(node, ["title"])
            link = get_text(node, ["link"])
            desc = get_text(node, ["description", "encoded"])
            pub = get_text(node, ["pubDate", "published", "updated"])
            if title and link:
                items.append({"title_en": title, "url": link, "description_en": desc[:1000], "published_raw": pub, "source": name, "source_type": kind})
        if not items:
            atom = "{http://www.w3.org/2005/Atom}"
            for node in root.findall(".//" + atom + "entry")[:35]:
                title = get_text(node, [atom + "title"])
                link = ""
                for le in node.findall(atom + "link"):
                    href = le.attrib.get("href", "")
                    if href and le.attrib.get("rel", "alternate") == "alternate":
                        link = href
                        break
                desc = get_text(node, [atom + "summary", atom + "content"])
                pub = get_text(node, [atom + "published", atom + "updated"])
                if title and link:
                    items.append({"title_en": title, "url": link, "description_en": desc[:1000], "published_raw": pub, "source": name, "source_type": kind})
        print(f"{name}: {len(items)} items")
        return items
    except Exception as e:
        print(f"Feed failed {name}: {e}")
        return []


def parse_date(s):
    if not s:
        return ""
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(BEIJING).isoformat()
    except Exception:
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(BEIJING).isoformat()
        except Exception:
            return ""


def category_for(item):
    text = (item.get("title_en", "") + " " + item.get("description_en", "")).lower()
    for category, patterns in CATEGORIES.items():
        if any(re.search(pattern, text, re.I) for pattern in patterns):
            return category
    return "行业与研究"


def translate_google(text):
    params = urllib.parse.urlencode({"client": "gtx", "sl": "auto", "tl": "zh-CN", "dt": "t", "q": text[:1200]})
    req = urllib.request.Request("https://translate.googleapis.com/translate_a/single?" + params,
                                 headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=12) as response:
        data = json.loads(response.read().decode("utf-8"))
    return "".join(part[0] for part in data[0] if part and part[0]).strip()


def translate_mymemory(text):
    params = urllib.parse.urlencode({"q": text[:450], "langpair": "en|zh-CN"})
    req = urllib.request.Request("https://api.mymemory.translated.net/get?" + params,
                                 headers={"User-Agent": "ZhixinAIDaily/2.1"})
    with urllib.request.urlopen(req, timeout=12) as response:
        data = json.loads(response.read().decode("utf-8"))
    result = data.get("responseData", {}).get("translatedText", "")
    if str(data.get("responseStatus")) != "200" or not result:
        raise RuntimeError("translation service unavailable")
    return clean(result)


def translate(text):
    text = (text or "").strip()
    if not text:
        return ""
    for fn in (translate_google, translate_mymemory):
        try:
            result = fn(text)
            if result:
                time.sleep(0.2)
                return result
        except Exception as exc:
            print(f"Translation service {fn.__name__} failed: {exc}")
    return ""


def daily_summary(news):
    if not news:
        return "今天没有成功采集到符合条件的资讯，请检查新闻源后重新运行。"
    counts = {}
    for item in news:
        counts[item["category"]] = counts.get(item["category"], 0) + 1
    dist = "；".join(f"{k} {v} 条" for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:5])
    highlights = "；".join((x.get("title_zh") or x["title_en"]) for x in news[:3])
    return (f"今日共采集 {len(news)} 条近 10 天资讯。赛道分布：{dist}。优先浏览：{highlights}。"
            "本总结依据新闻标题、来源和分类自动整理，不代表对新闻事实或技术效果的独立验证；重要结论请查看原文。")


def main():
    try:
        with open(OUT, "r", encoding="utf-8") as f:
            old_data = json.load(f)
        old_news = old_data.get("news", [])
    except Exception:
        old_news = []
    old_by_url = {x.get("url"): x for x in old_news if x.get("url")}

    all_items = []
    for name, url, kind in FEEDS:
        all_items.extend(parse_feed(name, url, kind))

    seen, unique = set(), []
    for item in all_items:
        key = item["url"].split("?")[0].rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        item["category"] = category_for(item)
        item["published_at"] = parse_date(item.pop("published_raw", ""))
        unique.append(item)

    cutoff = datetime.now(timezone.utc) - timedelta(days=10)
    recent = []
    for item in unique:
        try:
            dt = datetime.fromisoformat(item["published_at"])
            if dt.astimezone(timezone.utc) >= cutoff:
                recent.append(item)
        except Exception:
            recent.append(item)
    recent.sort(key=lambda x: x.get("published_at", ""), reverse=True)

    selected, counts = [], {}
    for item in recent:
        cat = item["category"]
        if counts.get(cat, 0) < 5 and len(selected) < 25:
            selected.append(item)
            counts[cat] = counts.get(cat, 0) + 1
    if len(selected) < 12:
        used = {x["url"] for x in selected}
        for item in recent:
            if item["url"] not in used:
                selected.append(item)
                if len(selected) >= 20:
                    break
    selected = selected[:25]

    final = []
    for item in selected:
        old = old_by_url.get(item["url"], {})
        title_zh = old.get("title_zh", "")
        if not title_zh or title_zh == item["title_en"]:
            title_zh = translate(item["title_en"]) or item["title_en"]
        old_summary = old.get("summary_zh", "")
        desc = item.get("description_en", "").strip()
        if old_summary and "生成失败" not in old_summary and "摘要暂不可用" not in old_summary:
            summary_zh = old_summary
        elif desc:
            summary_zh = translate(desc[:650]) or "原文摘要暂不可用；请点击“阅读原文”查看详情。"
        else:
            summary_zh = "该来源未提供摘要；请点击“阅读原文”查看详情。"
        why = WHY.get(item["category"], WHY["行业与研究"])
        if title_zh == item["title_en"]:
            why += " 标题翻译暂不可用，请结合英文原文判断。"
        final.append({
            "title_en": item["title_en"], "title_zh": title_zh, "summary_zh": summary_zh,
            "why_it_matters": why, "url": item["url"], "source": item["source"],
            "source_type": item["source_type"], "category": item["category"],
            "published_at": item.get("published_at", "")
        })

    counts = {}
    for item in final:
        counts[item["category"]] = counts.get(item["category"], 0) + 1
    takeaways = [f"今日采集较多的方向：{k}（{v} 条）。" for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:3]]
    while len(takeaways) < 3:
        takeaways.append("重要结论请优先核对官方公告、原始论文或可复现代码。")

    output = {
        "updated_at": datetime.now(BEIJING).isoformat(),
        "daily_summary_zh": daily_summary(final),
        "takeaways_zh": takeaways[:3],
        "news": final,
        "source_count": len(FEEDS),
        "note": "免密钥公共翻译服务可能限流；翻译失败时保留英文原文。每日总结是基于标题、来源和分类的规则归纳，不是大模型深度分析。请通过原文核验重要信息。"
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT}: {len(final)} stories")


if __name__ == "__main__":
    main()
