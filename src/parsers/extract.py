"""
文章正文与配图抽取（用于「故事直接摘抄」）

策略：
  - 正文优先用 trafilatura 抽取（质量好、自动去导航/广告）；
  - 配图从 og:image / twitter:image / 首图获取；
  - 二者均失败则退化为 BeautifulSoup 纯文本抽取。
"""
import logging
import requests
from bs4 import BeautifulSoup
from ..utils import abs_url

logger = logging.getLogger(__name__)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

try:
    import trafilatura
    _HAVE_TF = True
except Exception as e:  # pragma: no cover
    _HAVE_TF = False
    logger.warning(f"trafilatura 不可用，正文抽取退化为 BeautifulSoup: {e}")


def fetch_html(url: str, timeout: int = 20) -> str:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
        if r.status_code == 200 and r.text:
            return r.text
    except Exception as e:
        logger.debug(f"抓取页面失败 {url}: {e}")
    return ""


def _content_from_html(html: str, url: str = "") -> str:
    if not html:
        return ""
    if _HAVE_TF:
        try:
            txt = trafilatura.extract(
                html, url=url or None,
                include_comments=False, favor_precision=True,
            )
            if txt and len(txt.strip()) > 120:
                return txt.strip()
        except Exception as e:
            logger.debug(f"trafilatura 抽取失败: {e}")
    # 兜底：readability（若已安装）
    try:
        from readability import Document
        doc = Document(html)
        soup = BeautifulSoup(doc.summary(), "html.parser")
        txt = soup.get_text("\n", strip=True)
        if len(txt) > 120:
            return txt
    except Exception:
        pass
    # 最后兜底：去脚本/样式后取正文
    try:
        soup = BeautifulSoup(html, "html.parser")
        for t in soup(["script", "style", "noscript"]):
            t.decompose()
        return soup.get_text("\n", strip=True)
    except Exception:
        return ""


def _image_from_html(html: str, base_url: str = "") -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for prop in ("og:image", "og:image:url", "og:image:secure_url"):
        tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        if tag and tag.get("content"):
            return abs_url(base_url, tag["content"])
    tag = soup.find("meta", attrs={"name": "twitter:image"})
    if tag and tag.get("content"):
        return abs_url(base_url, tag["content"])
    img = soup.find("img", src=True)
    if img and img.get("src"):
        src = img["src"]
        if src.startswith("//"):
            src = "https:" + src
        if src.startswith("http"):
            return src
        return abs_url(base_url, src)
    return ""


def extract_article(url: str, timeout: int = 20):
    """抓取文章页，返回 (正文文本, 配图URL)；失败返回 ('', '')"""
    html = fetch_html(url, timeout)
    if not html:
        return "", ""
    content = _content_from_html(html, url)
    if content:
        content = content[:4000]
    image = _image_from_html(html, url)
    return content, image
