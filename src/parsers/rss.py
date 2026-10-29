"""
RSS / Atom 源解析器（故事版：抽取正文与配图，直接摘抄）
"""
import logging
from typing import List
from datetime import datetime
import feedparser
from bs4 import BeautifulSoup

from ..models import Article, SourceConfig
from ..utils import clean_text, normalize_date, abs_url
from .extract import extract_article, _image_from_html

logger = logging.getLogger(__name__)


def _image_from_entry(entry) -> str:
    for e in (entry.get("enclosures") or []):
        if isinstance(e, dict) and str(e.get("type") or "").startswith("image") and e.get("href"):
            return e["href"]
    for m in (entry.get("media_content") or []):
        if isinstance(m, dict) and m.get("medium") == "image" and m.get("url"):
            return m["url"]
    for m in (entry.get("media_thumbnail") or []):
        if isinstance(m, dict) and m.get("url"):
            return m["url"]
    return ""


def parse_feed(config: SourceConfig) -> List[Article]:
    """解析 RSS/Atom 订阅源，并抽取正文与配图"""
    articles = []
    try:
        feed = feedparser.parse(config.url)
    except Exception as e:
        logger.error(f"RSS parse error [{config.name}]: {e}")
        return articles

    for entry in feed.entries[:config.max_items]:
        try:
            title = clean_text(entry.get("title", ""))
            link = abs_url(config.url, entry.get("link", ""))
            if not title or not link:
                continue

            summary = clean_text(entry.get("summary", entry.get("description", "")))
            if summary:
                summary = BeautifulSoup(summary, "html.parser").get_text(" ")
            published = entry.get("published", entry.get("updated", ""))
            author = clean_text(entry.get("author", ""))
            tags = [t.term for t in entry.get("tags", []) if hasattr(t, "term")]

            # 正文：优先用 RSS 自带 content:encoded / description
            feed_html = ""
            for c in (entry.get("content") or []):
                v = c.get("value", "")
                if v:
                    feed_html = v
                    break
            if not feed_html:
                feed_html = entry.get("summary", "") or entry.get("description", "")
            content = ""
            if feed_html:
                txt = BeautifulSoup(feed_html, "html.parser").get_text("\n", strip=True)
                if len(txt) > 250:
                    content = txt[:4000]

            # 配图：优先 RSS enclosure / media
            image = _image_from_entry(entry)

            # 正文过短或缺少配图时，抓取原页面补全
            if (len(content) < 250 or not image) and link:
                page_content, page_image = extract_article(link)
                if len(content) < 250 and page_content:
                    content = page_content
                if not image and page_image:
                    image = page_image

            if not summary and content:
                summary = content[:200]

            articles.append(Article(
                title=title,
                url=link,
                category=config.category,
                source=config.name,
                source_url=config.url,
                published=normalize_date(published) or datetime.now().isoformat()[:10],
                summary=summary[:500],
                content=content,
                image=image,
                author=author,
                tags=tags,
                language=config.language,
                country=config.country,
                region=config.region,
                extra={"feed_type": feed.version if hasattr(feed, "version") else "unknown"},
            ))
        except Exception as e:
            logger.warning(f"Skip RSS entry in {config.name}: {e}")
            continue
    logger.info(f"[{config.name}] RSS parsed {len(articles)} items")
    return articles
