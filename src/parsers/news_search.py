"""
按关键词检索故事/资讯的解析器（主题发现）

  provider: google   → Google News RSS（覆盖好，含中文媒体）
  provider: gdelt    → GDELT DOC API（JSON，长期可用，作为 Google 的自动兜底）

故事类条目以「链接 + 摘要」呈现；GDELT 直链会尝试抓取正文与配图。
"""
import base64
import logging
import re
import threading
import time
from datetime import datetime, timezone
from typing import List
from urllib.parse import urlencode

import feedparser
import requests
from bs4 import BeautifulSoup

from ..models import Article, SourceConfig
from ..utils import clean_text, normalize_date, normalize_content
from .extract import extract_article

logger = logging.getLogger(__name__)

GOOGLE_NEWS_ENDPOINT = "https://news.google.com/rss/search"
GDELT_ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"

# GDELT DOC API 对每个 IP 限速「5 秒 1 次」，超出的请求返回一行纯文本提示而不是 JSON。
# 采集器用 8 线程并发，所以在持锁状态下强制间隔：否则 provider: gdelt 的源基本全抓空。
_GDELT_MIN_INTERVAL = 5.0
_GDELT_LOCK = threading.Lock()
_GDELT_LAST = [0.0]


def _gdelt_slot() -> None:
    with _GDELT_LOCK:
        wait = _GDELT_MIN_INTERVAL - (time.monotonic() - _GDELT_LAST[0])
        if wait > 0:
            time.sleep(wait)
        _GDELT_LAST[0] = time.monotonic()


UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def parse_news_search(config: SourceConfig) -> List[Article]:
    """按配置里的关键词检索，Google News 优先，GDELT 兜底"""
    extra = config.extra or {}
    query = clean_text(extra.get("query") or config.name)
    if not query:
        logger.warning(f"[{config.name}] news_search 缺少 query")
        return []

    preferred = (extra.get("provider") or "google").lower()
    order = [preferred] + [p for p in ("google", "gdelt") if p != preferred]
    ladder = _relax_ladder(query)

    for provider in order:
        if provider not in ("google", "gdelt"):
            continue
        for q in ladder:
            try:
                if provider == "google":
                    items = _fetch_google(q, config)
                else:
                    items = _fetch_gdelt(q, config)
            except Exception as e:
                logger.debug(f"[{config.name}] {provider} 检索失败: {e}")
                items = []

            if items:
                note = "" if q == query else f"，原词 {query!r} 过窄已放宽"
                logger.info(f"[{config.name}] {provider} 检索到 {len(items)} 条（关键词：{q}{note}）")
                return items
        logger.debug(f"[{config.name}] {provider} 无结果，切换下一个 provider")

    logger.info(f"[{config.name}] 全部 provider 无结果（关键词：{query}）")
    return []


def _relax_ladder(query: str) -> List[str]:
    """Google News 把空格当 AND，词一多就 0 条；逐级去掉尾部词，保留前两词为主旨"""
    terms = query.split()
    if len(terms) < 3:
        return [query]
    ladder = [query] + [" ".join(terms[:n]) for n in range(len(terms) - 1, 1, -1)]
    seen, out = set(), []
    for q in ladder:
        # 去掉尾部词可能把 OR/AND 孤零零留在句尾，那是无效查询
        if q in seen or re.search(r"\b(OR|AND)$", q, re.IGNORECASE):
            continue
        seen.add(q)
        out.append(q)
    return out


def _enrich(url: str) -> (str, str):
    """尝试抓取正文与配图（GDELT 直链有效；Google News 直链通常无法抽取）"""
    try:
        content, image = extract_article(url, timeout=15)
        if len(content or "") < 250:
            content = ""
        return content or "", image or ""
    except Exception:
        return "", ""


# ---------- Google News RSS ----------

# 各地区版位的界面语言 / 文字代码。全球搜罗要靠这些版位才能拿到本地网站的结果。
HL_BY_LANG = {
    "en": "en-US", "zh": "zh-CN", "ja": "ja", "ko": "ko", "id": "id",
    "fr": "fr", "pt": "pt-BR", "es": "es-419", "de": "de", "it": "it",
    "ru": "ru", "ar": "ar", "tr": "tr", "hi": "hi", "sw": "sw",
    "nl": "nl", "pl": "pl", "uk": "uk",
}
SCRIPT_BY_LANG = {
    "en": "en", "zh": "zh-Hans", "ja": "ja", "ko": "ko", "id": "id",
    "fr": "fr", "pt": "pt-BR", "es": "es-419", "de": "de", "it": "it",
    "ru": "ru", "ar": "ar", "tr": "tr", "hi": "hi", "sw": "sw",
    "nl": "nl", "pl": "pl", "uk": "uk",
}


def _google_locale_variants(config: SourceConfig) -> List[dict]:
    """按 country/language 给出 Google News 版位候选，覆盖全球多语种版位。

    gl 决定地区版、hl 决定检索语言、ceid 是「地区:文字」。中文繁体地区单独处理；
    若某个组合 Google 不认（返回空 feed），再退回该语言的通用版位。
    """
    country = (config.country or "").strip().upper() or "US"
    lang = (config.language or "en").strip().lower().split("-")[0]

    if lang == "zh":
        hl = {"TW": "zh-TW", "HK": "zh-HK", "MO": "zh-MO"}.get(country, "zh-CN")
        script = "zh-Hant" if country in ("TW", "HK", "MO") else "zh-Hans"
        generic = {"hl": "zh-CN", "gl": "CN", "ceid": "CN:zh-Hans"}
    else:
        hl = HL_BY_LANG.get(lang, "en-US")
        script = SCRIPT_BY_LANG.get(lang, "en")
        if lang == "es" and country == "ES":
            hl, script = "es", "es"
        generic = {"hl": "en-US", "gl": "US", "ceid": "US:en"}

    exact = {"hl": hl, "gl": country, "ceid": f"{country}:{script}"}
    variants = [exact] if exact == generic else [exact, generic]
    # 另一个兜底：同语言但用美国版位，许多地区组合被 Google 拒时仍能出结果
    if lang not in ("en", "zh"):
        variants.append({"hl": hl, "gl": "US", "ceid": f"US:{script}"})
    return variants


# Google News RSS 的 link 是 /rss/articles/<base64>，不是原文地址。
# 尽力解出真实 URL：先解 base64 里内嵌的链接，再跟随一次重定向（限量，避免拖慢采集）。
_RESOLVE_BUDGET = [60]
_RESOLVE_LOCK = threading.Lock()


def _decode_google_url(url: str) -> str:
    m = re.search(r"/articles/([A-Za-z0-9_\-]{8,})", url or "")
    if not m:
        return ""
    token = m.group(1)
    try:
        raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
        for u in re.findall(rb"https?://[\x20-\x7e]+", raw):
            candidate = re.split(r"[\x00-\x1f\x7f]", u.decode("utf-8", "ignore"))[0]
            if "news.google.com" not in candidate and len(candidate) > 20:
                return candidate
    except Exception:
        pass
    return ""


def _follow_redirect(url: str) -> str:
    with _RESOLVE_LOCK:
        if _RESOLVE_BUDGET[0] <= 0:
            return ""
        _RESOLVE_BUDGET[0] -= 1
    try:
        resp = requests.head(url, headers={"User-Agent": UA}, allow_redirects=True, timeout=5)
        final = resp.url or ""
        if final and "news.google.com" not in final:
            return final
    except Exception:
        pass
    return ""


def _resolve_article_url(link: str) -> (str, str):
    real = _decode_google_url(link)
    if not real:
        real = _follow_redirect(link)
    return real, link


def _fetch_google(query: str, config: SourceConfig) -> List[Article]:
    entries = []
    for locale in _google_locale_variants(config):
        params = {"q": query}
        params.update(locale)
        url = f"{GOOGLE_NEWS_ENDPOINT}?{urlencode(params)}"
        try:
            resp = requests.get(url, headers={"User-Agent": UA, "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8"}, timeout=25)
        except Exception as exc:
            logger.debug(f"[{config.name}] google_news {locale['ceid']} 请求失败: {exc}")
            continue
        if resp.status_code != 200:
            continue
        parsed = feedparser.parse(resp.content)
        if parsed.entries:
            entries = parsed.entries[:config.max_items]
            break

    if not entries:
        return []

    articles: List[Article] = []
    for entry in entries:
        title = clean_text(entry.get("title", ""))
        link = entry.get("link", "")
        if not title or not link:
            continue

        publisher = ""
        if " - " in title:
            head, tail = title.rsplit(" - ", 1)
            if head and tail:
                title, publisher = head.strip(), tail.strip()

        summary = entry.get("summary", "") or ""
        if summary:
            summary = clean_text(BeautifulSoup(summary, "html.parser").get_text(" "))

        published = normalize_date(entry.get("published", "") or entry.get("updated", ""))
        if not published:
            published = _structured_date(entry)

        real_url, google_url = _resolve_article_url(link)
        articles.append(Article(
            title=title,
            url=real_url or link,
            category=config.category,
            source=config.name,
            source_url=config.url,
            published=published or datetime.now(timezone.utc).astimezone().isoformat()[:10],
            summary=summary[:500],
            author=publisher,
            language=config.language,
            country=config.country,
            region=config.region,
            extra={
                "provider": "google_news", "query": query, "publisher": publisher,
                "google_url": google_url, "resolved": bool(real_url),
            },
        ))
    return articles


def _structured_date(entry) -> str:
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            try:
                return datetime(*value[:3]).strftime("%Y-%m-%d")
            except Exception:
                pass
    return ""


# ---------- GDELT DOC API ----------

def _fetch_gdelt(query: str, config: SourceConfig) -> List[Article]:
    params = {
        "query": query,
        "mode": "artlist",
        "format": "json",
        "maxrecords": min(config.max_items * 2, 75),
        "timespan": "30d",
        "sort": "datedesc",
    }
    headers = {"User-Agent": UA, "Accept": "application/json"}
    _gdelt_slot()
    resp = requests.get(GDELT_ENDPOINT, params=params, headers=headers, timeout=30)
    if resp.status_code != 200 or not resp.text.strip().startswith("{"):
        return []

    data = resp.json()
    articles: List[Article] = []
    for item in data.get("articles", [])[:config.max_items]:
        title = clean_text(item.get("title", ""))
        url = item.get("url", "")
        if not title or not url:
            continue

        published = _gdelt_date(item.get("seendate", ""))
        content, image = _enrich(url)

        articles.append(Article(
            title=title,
            url=url,
            category=config.category,
            source=config.name,
            source_url=config.url,
            published=published,
            summary=content[:200] if content else "",
            content=content,
            image=image,
            author=item.get("domain", ""),
            language=config.language,
            country=config.country,
            region=config.region,
            extra={"provider": "gdelt", "query": query, "domain": item.get("domain", "")},
        ))
    return articles


def _gdelt_date(seendate: str) -> str:
    seendate = (seendate or "").strip()
    if len(seendate) >= 8 and seendate[:8].isdigit():
        return f"{seendate[:4]}-{seendate[4:6]}-{seendate[6:8]}"
    return ""
