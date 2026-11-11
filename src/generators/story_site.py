"""
全球搜罗 · 静态站点生成器

唯一数据源：data/db/articles.json
  自动从全世界网站搜罗、经故事判别、译中后的真实故事。

输出：
  site/index.html                 首页（最新搜罗 / 按地区 / 主题书架）
  site/latest.html                最新搜罗（按时间）
  site/regions.html               按地区
  site/all.html                   全部故事（按主题）
  site/categories/<key>.html      6 个分类页
  site/story/<id>.html            每篇故事的独立阅读页
  site/about.html                 全球搜罗说明
  site/sources.html               旧链接兼容跳转
"""
import os
import re
import json
import glob
import shutil
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)
HK_TZ = timezone(timedelta(hours=8))

CATEGORIES = [
    {"key": "china", "label": "中国故事", "icon": "🏮",
     "desc": "这片土地上的宣教士、传道人与战火里的普通人。"},
    {"key": "africa", "label": "非洲宣教与见证", "icon": "🌍",
     "desc": "非洲大陆的宣教士、本地传道人，以及村落、医院与部落里的故事。"},
    {"key": "missionary", "label": "宣教士故事", "icon": "🧭",
     "desc": "离开故土、把一生放在异乡的人。"},
    {"key": "giant", "label": "属灵伟人", "icon": "📖",
     "desc": "教会历史里被反复讲述的名字，以及他们不太被讲述的软弱。"},
    {"key": "trial", "label": "患难中的信心", "icon": "🔥",
     "desc": "监狱、集中营、逼迫与长矛之下，人怎样仍然选择不恨。"},
    {"key": "lay", "label": "平凡人的见证", "icon": "🤝",
     "desc": "没有头衔、没有讲台，却把一生过成了一篇讲章的人。"},
]
CATEGORY_MAP = {c["key"]: c for c in CATEGORIES}
REGIONS = ["非洲", "中国", "中东", "亚洲", "拉美", "欧洲", "北美", "大洋洲", "全球"]

COMING_SOON = [
    "柏格理与石门坎：把文字给一个民族",
    "富能仁：傈僳山雨中的祷告",
    "宋尚节：一把火烧掉的文凭",
    "马偕与巴克礼：台湾早期的两盏灯",
    "李文斯顿：非洲心脏里的一盏灯",
    "玛丽·斯莱索：卡拉巴尔的白人母亲",
    "耶德逊：缅甸二十年与一本字典",
    "温伯兰：狱中十四年的讲道",
    "苏珊娜·卫斯理：一周一个晚上，单独陪一个孩子",
]


def now_hk() -> str:
    return datetime.now(HK_TZ).strftime("%Y-%m-%d %H:%M")


def _plain(text: str, limit: int = 0) -> str:
    s = re.sub(r"\s+", " ", str(text or "")).strip()
    return s[:limit] if limit else s


class StorySiteGenerator:
    def __init__(self, site_dir: str, template_dir: str,
                 db_dir: str = None, headers_file: str = None):
        self.site_dir = site_dir
        self.template_dir = template_dir
        self.db_dir = db_dir
        self.headers_file = headers_file
        self.env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)
        self.stories: List[Dict[str, Any]] = []

    # ---------- 校验：搜罗库 ----------
    def validate(self) -> List[str]:
        problems: List[str] = []
        if not self.db_dir:
            return problems
        path = os.path.join(self.db_dir, "articles.json")
        if not os.path.exists(path):
            return problems
        try:
            with open(path, "r", encoding="utf-8") as f:
                db = json.load(f)
        except Exception as e:
            return [f"articles.json：JSON 解析失败 - {e}"]
        items = db.get("articles", [])
        if not isinstance(items, list):
            return ["articles.json：articles 应为数组"]
        seen = set()
        for i, a in enumerate(items):
            extra = a.get("extra") or {}
            # 旧新闻库遗留条目不进故事站，也不参与校验
            if not extra.get("story_score"):
                continue
            if not (a.get("title_zh") or a.get("title")):
                problems.append(f"articles[{i}]：缺少标题")
            sid = a.get("id")
            if sid and sid in seen:
                problems.append(f"articles[{i}]：id 重复 {sid}")
            seen.add(sid)
        return problems

    # ---------- 数据工具 ----------
    @staticmethod
    def _minutes_of(body: List[str]) -> int:
        chars = sum(len(p) for p in body)
        return max(2, round(chars / 400))

    @staticmethod
    def _search_text(s: Dict[str, Any]) -> str:
        parts = [s.get("title", ""), s.get("subtitle", ""), s.get("hook", ""),
                 s.get("people", ""), s.get("place", ""), s.get("era", ""),
                 s.get("source_name", ""), " ".join(s.get("tags", []))]
        return " ".join(str(p) for p in parts).lower()

    # ---------- 数据：全球搜罗库 ----------
    def _load_collected(self) -> List[Dict[str, Any]]:
        if not self.db_dir:
            return []
        path = os.path.join(self.db_dir, "articles.json")
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                db = json.load(f)
        except Exception as e:
            logger.warning(f"读取搜罗库失败：{e}")
            return []

        out: List[Dict[str, Any]] = []
        raw_items = db.get("articles", [])
        for a in raw_items:
            extra = a.get("extra") or {}
            # 兼容旧新闻库：没有故事判别分数的条目一律不进故事站
            if not extra.get("story_score"):
                continue
            title = a.get("title_zh") or a.get("title") or ""
            if not title:
                continue
            original = a.get("title") or ""
            body_text = a.get("content_zh") or a.get("content") or ""
            summary = a.get("summary_zh") or a.get("summary") or ""
            paragraphs = [p.strip() for p in body_text.split("\n") if p.strip()]
            if not paragraphs:
                paragraphs = [_plain(summary, 400) or "（原文未提供正文，请点击文末链接阅读原文。）"]
            paragraphs = paragraphs[:80]

            hook = _plain(summary, 110) or _plain(paragraphs[0], 110)
            if not hook:
                hook = "来自全球网站的一则真实故事。"
            published = (a.get("published") or "")[:10]
            source_name = a.get("source") or extra.get("publisher") or extra.get("domain") or "网络来源"
            region = a.get("region") or "全球"
            category = a.get("category") if a.get("category") in CATEGORY_MAP else "lay"
            lang = (a.get("language") or "en").lower()[:2]

            s: Dict[str, Any] = {
                "origin": "collected",
                "id": "s-" + (a.get("id") or str(len(out))),
                "url": f"story/s-{a.get('id') or len(out)}.html",
                "title": title,
                "subtitle": ("原题：" + original) if original and original != title
                            else f"{source_name} · {published or '近期'}",
                "hook": hook,
                "body": paragraphs,
                "sources": [f"原始出处：{source_name}", a.get("url") or ""],
                "source_url": a.get("url") or "",
                "source_name": source_name,
                "published": published,
                "era": published or "近期",
                "place": region,
                "people": a.get("author") or source_name,
                "tags": (a.get("tags") or [])[:8],
                "image": a.get("image") or "",
                "category": category,
                "cat": CATEGORY_MAP[category],
                "region": region,
                "minutes": self._minutes_of(paragraphs),
                "machine": bool(a.get("content_zh")) and lang != "zh",
                "story_score": extra.get("story_score", 0),
                "featured": extra.get("story_score", 0) >= 8,
                "_cat_order": 99,
            }
            s["search"] = self._search_text(s)
            out.append(s)

        out.sort(key=lambda s: (s.get("published") or ""), reverse=True)
        return out

    # ---------- 输出 ----------
    def _clean_generated(self):
        for sub in ("categories", "story"):
            dirpath = os.path.join(self.site_dir, sub)
            os.makedirs(dirpath, exist_ok=True)
            for old in glob.glob(os.path.join(dirpath, "*.html")):
                os.remove(old)

    def _copy_headers(self):
        if self.headers_file and os.path.exists(self.headers_file):
            shutil.copyfile(self.headers_file, os.path.join(self.site_dir, "_headers"))

    def _write(self, rel_path: str, html: str):
        out = os.path.join(self.site_dir, rel_path)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(html)

    def _common(self, root: str = "", **kwargs) -> Dict[str, Any]:
        ctx = dict(root=root, categories=CATEGORIES, regions=REGIONS,
                   total=len(self.stories), updated_at=now_hk(),
                   coming_soon=COMING_SOON)
        ctx.update(kwargs)
        return ctx

    def _tag_cloud(self, top: int = 24) -> List[Dict[str, Any]]:
        counts: Dict[str, int] = {}
        for s in self.stories:
            for t in s.get("tags", []):
                counts[t] = counts.get(t, 0) + 1
        return [{"name": k, "count": v}
                for k, v in sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:top]]

    def generate(self):
        problems = self.validate()
        if problems:
            raise ValueError("搜罗故事库校验未通过：\n  - " + "\n  - ".join(problems))

        self.stories = self._load_collected()

        os.makedirs(self.site_dir, exist_ok=True)
        self._clean_generated()
        self._copy_headers()

        by_cat = {c["key"]: [s for s in self.stories if s["category"] == c["key"]]
                  for c in CATEGORIES}
        by_region = {r: [s for s in self.stories if s["region"] == r] for r in REGIONS}
        region_stats = [{"name": r, "count": len(by_region[r])}
                        for r in REGIONS if by_region[r]]
        latest = self.stories[:18]
        featured = [s for s in self.stories if s.get("featured")][:6]
        tag_cloud = self._tag_cloud()

        domains, filter_stats = [], {}
        if self.db_dir:
            for name, holder in (("discovered_domains.json", "domains"),
                                 ("filter_stats.json", "stats")):
                p = os.path.join(self.db_dir, name)
                if os.path.exists(p):
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        if holder == "domains":
                            domains = data.get("domains", [])
                        else:
                            filter_stats = data
                    except Exception:
                        pass

        sources_count = 0
        try:
            from ..config_loader import load_sources
            cfg = os.path.join(os.path.dirname(os.path.dirname(self.db_dir or "")),
                               "config", "sources.yaml") if self.db_dir else ""
            if cfg:
                sources_count = len(load_sources(cfg).get("sources", []))
        except Exception:
            pass

        stats = {
            "collected": len(self.stories),
            "domains": len(domains),
            "sources_count": sources_count,
            "filter": filter_stats,
            "latest_date": self.stories[0]["published"] if self.stories else "",
        }

        # 首页
        self._write("index.html", self.env.get_template("index.html").render(
            **self._common("", featured=featured, latest=latest, by_cat=by_cat,
                           by_region=by_region, region_stats=region_stats,
                           tag_cloud=tag_cloud, stats=stats, page="home")
        ))
        self._write("latest.html", self.env.get_template("latest.html").render(
            **self._common("", latest=self.stories[:120], tag_cloud=tag_cloud,
                           stats=stats, page="latest")
        ))
        self._write("regions.html", self.env.get_template("regions.html").render(
            **self._common("", by_region=by_region, region_stats=region_stats,
                           stats=stats, page="regions")
        ))
        self._write("all.html", self.env.get_template("all.html").render(
            **self._common("", by_cat=by_cat, tag_cloud=tag_cloud,
                           stats=stats, page="all")
        ))

        cat_tpl = self.env.get_template("category.html")
        for cat in CATEGORIES:
            self._write(f"categories/{cat['key']}.html", cat_tpl.render(
                **self._common("../", cat=cat, stories=by_cat[cat["key"]],
                               tag_cloud=tag_cloud, stats=stats, page="cat")
            ))

        story_tpl = self.env.get_template("story.html")
        for i, s in enumerate(self.stories):
            self._write(f"story/{s['id']}.html", story_tpl.render(
                **self._common("../", s=s,
                               prev=self.stories[i - 1] if i > 0 else None,
                               nxt=self.stories[i + 1] if i + 1 < len(self.stories) else None,
                               more=[x for x in by_cat[s["category"]] if x["id"] != s["id"]][:3],
                               page="story")
            ))

        self._write("about.html", self.env.get_template("about.html").render(
            **self._common("", domains=domains, stats=stats, page="about")
        ))
        self._write("sources.html", self.env.get_template("redirect.html").render(
            **self._common("", page="about")
        ))

        logger.info(
            f"站点已生成：全球搜罗 {len(self.stories)} 篇，"
            f"{len(self.stories)} 个阅读页 → {self.site_dir}"
        )
        return len(self.stories)
