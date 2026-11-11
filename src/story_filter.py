"""
故事判别与归类

搜罗范围是全世界的网站，但收进来的必须是「故事」：
真人、真事、有经历和转折。新闻简讯、书评书摘、灵修小品、神学评论、
讲章、播客、活动通知、募捐、榜单……一律挡在外面。

对外只暴露 filter_and_classify(articles) -> 保留下来的 Article 列表，
并就地写入 category / region / tags / extra['story_score'] 等字段。
"""
import re
import logging
from typing import List, Dict, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ---------- 直接排除：这些不是故事 ----------
REJECT_PATTERNS = [
    # 书籍 / 书评 / 书摘（用户明确说「不是书籍」）
    r"book review", r"book excerpt", r"excerpt from", r"review:\s", r"\breview\b.{0,20}\bbook\b",
    r"new book", r"book release", r"author interview about", r"reading list", r"top \d+ books",
    r"书评", r"书摘", r"新书", r"读书笔记", r"荐书", r"节选自", r"本书", r"书目", r"读后感和",
    # 灵修 / 讲章 / 查经 / 神学
    r"daily devotion", r"devotional\b", r"bible study", r"sermon notes", r"\bsermon\b",
    r"theolog(y|ical)", r"doctrine", r"commentary", r"exegesis", r"verse of the day",
    r"灵修", r"每日灵粮", r"查经", r"讲章", r"神学", r"教义", r"释经", r"经文分享", r"每日经文",
    # 新闻形态：简讯 / 快讯 / 汇总 / 公告
    r"news roundup", r"weekly roundup", r"headlines", r"breaking news", r"press release",
    r"in the news", r"news brief", r"bulletin", r"statement on", r"official statement",
    r"一周要闻", r"简讯", r"快讯", r"要闻", r"公告", r"声明", r"新闻汇总", r"时事",
    # 活动 / 组织 / 行政
    r"conference (registration|schedule)", r"register now", r"\bwebinar\b", r"job opening",
    r"\bhiring\b", r"\bdonate\b", r"fundrais", r"annual report", r"give now",
    r"报名", r"活动通知", r"招聘", r"奉献", r"募捐", r"年会", r"会议议程", r"招募",
    # 媒体形态
    r"podcast episode", r"\bpodcast\b", r"watch (the|now)", r"video:", r"listen to",
    r"photo gallery", r"infographic", r"播客", r"视频", r"音频", r"直播",
    # 议论 / 观点 / 清单
    r"^opinion", r"opinion:", r"an open letter", r"why (we|the church|i) (need|should|must)",
    r"^\d+ (ways|things|reasons|lessons)", r"top \d+", r"quiz:",
    r"观点", r"社论", r"评论", r"公开信", r"\d+个方法", r"几个建议", r"问答",
]

# 非英语源的「非故事形态」标题：否则多语言条目放宽后会混进新闻与活动通知
I18N_REJECT = [
    # 法语
    r"communiqué", r"revue de presse", r"inscription", r"conférence", r"nouveau livre",
    r"podcast", r"à télécharger", r"brèves",
    # 葡语
    r"comunicado", r"inscrições", r"inscreva-se", r"novo livro", r"resenha", r"podcast",
    # 西语
    r"rueda de prensa", r"comunicado", r"inscripción", r"inscríbete", r"nuevo libro", r"reseña",
    # 印尼语
    r"siaran pers", r"pendaftaran", r"buku baru", r"ulasan buku", r"podcast", r"agenda acara",
    # 日语
    r"書評", r"新刊", r"講演会", r"集会案内", r"寄付のお願い", r"ポッドキャスト",
    # 韩语
    r"서평", r"신간", r"강연", r"행사 안내", r"후원 요청", r"팟캐스트",
]

# ---------- 故事正向信号 ----------
# 3 分：几乎可以确定是一篇人物故事 / 见证
STRONG = [
    r"testimony", r"testimonies", r"my (story|journey|conversion)", r"conversion story",
    r"life story", r"her story", r"his story", r"the story of", r"a story of",
    r"biography", r"biographical", r"born again", r"came to faith", r"found faith",
    r"from .{1,30} to .{1,30}", r"how (god|christ|jesus) (changed|saved|met|used|led)",
    r"he (was|had|grew|left|went|died|survived|spent)", r"she (was|had|grew|left|went|died|survived|spent)",
    r"见证", r"信主", r"悔改归主", r"生平", r"传记", r"一生", r"的故事", r"亲身经历",
    r"从.{1,20}到.{1,20}", r"他(如何|怎样|曾|在|被|带着)", r"她(如何|怎样|曾|在|被|带着)",
    r"蒙召", r"殉道", r"宣教士的", r"传道人的",
]
I18N_STRONG = [
    # 法语
    r"témoignage", r"témoignages", r"mon histoire", r"récit de vie", r"histoire de vie",
    r"biographie", r"la vie de", r"comment dieu a",
    # 葡语
    r"testemunho", r"testemunhos", r"minha história", r"história de vida",
    r"biografia", r"a vida de", r"como deus",
    # 西语
    r"testimonio", r"testimonios", r"mi historia", r"historia de vida",
    r"biografía", r"la vida de", r"cómo dios",
    # 印尼语
    r"kesaksian", r"kisah hidup", r"riwayat hidup", r"biografi", r"kisah tentang", r"hidupnya",
    # 日语
    r"証言", r"証し", r"生涯", r"伝記", r"宣教師の", r"物語",
    # 韩语
    r"간증", r"인생 이야기", r"전기", r"선교사의", r"이야기",
]
# 2 分：典型故事题材
MEDIUM = [
    r"missionary", r"missionaries", r"mission field", r"church planting", r"evangeli[sz]",
    r"persecut", r"martyr", r"imprison", r"prison", r"refugee", r"orphan", r"widow",
    r"village", r"tribe", r"jungle", r"desert", r"hospital", r"leprosy", r"famine",
    r"conversion", r"bapti[sz]", r"disciple", r"revival", r"prayer meeting",
    r"宣教", r"差会", r"拓荒", r"植堂", r"逼迫", r"患难", r"囚", r"难民", r"孤儿",
    r"乡村", r"部落", r"复兴", r"祷告", r"受洗", r"布道", r"传福音",
]
I18N_MEDIUM = [
    # 法语
    r"missionnaire", r"persécut", r"martyr", r"prison", r"réfugié", r"orphelin",
    r"village", r"tribu", r"église", r"évangile", r"baptême", r"réveil", r"hôpital",
    r"foi", r"converti",
    # 葡语
    r"missionário", r"persegui", r"mártir", r"prisão", r"refugiado", r"órfão",
    r"aldeia", r"tribo", r"igreja", r"evangelho", r"batismo", r"avivamento", r"hospital", r"fé",
    # 西语
    r"misionero", r"persecución", r"mártir", r"prisión", r"refugiado", r"huérfano",
    r"aldea", r"tribu", r"iglesia", r"evangelio", r"bautismo", r"avivamiento", r"hospital", r"fe",
    # 印尼语
    r"misionaris", r"penganiayaan", r"martir", r"penjara", r"pengungsi", r"yatim",
    r"desa", r"suku", r"gereja", r"injil", r"baptisan", r"kebangunan", r"iman",
    # 日语
    r"宣教師", r"宣教", r"迫害", r"殉教", r"投獄", r"難民", r"孤児", r"教会", r"福音", r"洗礼", r"信仰",
    # 韩语
    r"선교사", r"선교", r"박해", r"순교", r"투옥", r"난민", r"고아", r"교회", r"복음", r"세례", r"신앙",
]
# 1 分：叙事语气 / 时间线
NARRATIVE = [
    r"\bwhen\b", r"\bafter\b", r"\byears later\b", r"\beventually\b", r"\bone day\b",
    r"\bat the age of\b", r"\bgrew up\b", r"\bhis (wife|mother|father|family|son|daughter)\b",
    r"\bher (husband|mother|father|family|son|daughter)\b", r"\bin \d{4}\b",
    r"那年", r"后来", r"多年以后", r"有一天", r"小时候", r"临终", r"去世", r"终于",
]
I18N_NARRATIVE = [
    r"\bquand\b", r"\baprès\b", r"\bplus tard\b", r"\bun jour\b", r"\bdes années\b",
    r"\bquando\b", r"\bdepois\b", r"\banos depois\b", r"\bum dia\b", r"\bdurante anos\b",
    r"\bcuando\b", r"\bdespués\b", r"\baños después\b", r"\bdurante años\b",
    r"\bketika\b", r"\bsetelah\b", r"\bsuatu hari\b", r"\bbeberapa tahun\b", r"\bpada usia\b",
    r"その後", r"数年後", r"ある日", r"幼少期", r"歳のとき",
    r"그 후", r"몇 년 후", r"어느 날", r"어린 시절",
]
REJECT_RE = [re.compile(p, re.IGNORECASE) for p in REJECT_PATTERNS + I18N_REJECT]
STRONG_RE = [re.compile(p, re.IGNORECASE) for p in STRONG + I18N_STRONG]
MEDIUM_RE = [re.compile(p, re.IGNORECASE) for p in MEDIUM + I18N_MEDIUM]
NARRATIVE_RE = [re.compile(p, re.IGNORECASE) for p in NARRATIVE + I18N_NARRATIVE]

# ---------- 地区识别（全世界） ----------
REGION_RULES = [
    ("非洲", [r"\bafrica", r"afrique", r"\báfrica", r"nigeria", r"nigéria", r"kenya", r"uganda",
              r"tanzania", r"ghana", r"zambia", r"malawi", r"congo", r"rwanda", r"burundi",
              r"ethiopia", r"sudan", r"senegal", r"sénégal", r"cameroun", r"cameroon",
              r"côte d'ivoire", r"ivory coast", r"mozambique", r"madagascar", r"angola",
              r"zimbabwe", r"botswana", r"namibia", r"liberia", r"sierra leone", r"sahel",
              r"アフリカ", r"아프리카",
              r"非洲", r"尼日利亚", r"肯尼亚", r"乌干达", r"刚果", r"埃塞俄比亚", r"苏丹",
              r"加纳", r"赞比亚", r"马拉维", r"坦桑尼亚"]),
    ("中国", [r"\bchina\b", r"chinese", r"\btaiwan", r"hong kong", r"\bshanghai\b", r"\bbeijing\b",
              r"中国", r"华人", r"台灣", r"台湾", r"香港", r"山西", r"云南", r"内地会"]),
    ("中东", [r"\biran\b", r"\biraq\b", r"\bsyria\b", r"lebanon", r"\bisrael\b", r"\bgypt\b",
              r"egypt", r"\bturkey\b", r"\byemen\b", r"\bjordan\b", r"saudi", r"middle east",
              r"中东", r"伊朗", r"叙利亚", r"黎巴嫩", r"土耳其", r"埃及"]),
    ("亚洲", [r"\bindia\b", r"\bkorea\b", r"\bjapan\b", r"indonesia", r"indonésie", r"philippines",
              r"vietnam", r"thailand", r"myanmar", r"bangladesh", r"pakistan", r"nepal",
              r"cambodia", r"asia", r"日本", r"韓国", r"한국", r"インドネシア",
              r"亚洲", r"印度", r"韩国", r"日本", r"印尼", r"菲律宾", r"越南", r"缅甸"]),
    ("拉美", [r"brazil", r"brasil", r"brésil", r"mexico", r"méxico", r"argentina", r"colombia",
              r"peru", r"chile", r"bolivia", r"ecuador", r"guatemala", r"honduras",
              r"venezuela", r"latin america", r"amazon", r"amazônia", r"ブラジル",
              r"拉美", r"巴西", r"墨西哥", r"阿根廷", r"哥伦比亚", r"亚马逊"]),
    ("欧洲", [r"\buk\b", r"britain", r"england", r"scotland", r"germany", r"france", r"spain",
              r"italy", r"poland", r"ukraine", r"russia", r"europe", r"英国", r"德国", r"法国",
              r"欧洲", r"乌克兰", r"俄罗斯"]),
    ("北美", [r"\bunited states\b", r"\bamerica\b", r"\bcanada\b", r"\bu\.s\.", r"美国", r"加拿大"]),
    ("大洋洲", [r"australia", r"new zealand", r"papua", r"oceania", r"澳大利亚", r"新西兰", r"巴布亚"]),
]
REGION_RE = [(name, [re.compile(p, re.IGNORECASE) for p in pats]) for name, pats in REGION_RULES]

# ---------- 主题分类 ----------
TOPIC_RULES = [
    ("africa", [r"africa", r"afrique", r"áfrica", r"nigeria", r"nigéria", r"kenya", r"uganda",
                r"congo", r"アフリカ", r"아프리카", r"非洲"]),
    ("china", [r"china", r"chinese", r"中国", r"华人", r"台湾", r"香港"]),
    ("trial", [r"persecut", r"persécut", r"persegui", r"persecución", r"penganiayaan",
               r"martyr", r"mártir", r"imprison", r"prison", r"prisión", r"prisão", r"penjara",
               r"camp", r"torture", r"killed", r"迫害", r"殉教", r"박해", r"순교",
               r"逼迫", r"殉道", r"集中营", r"囚禁", r"患难", r"受苦"]),
    ("giant", [r"biography", r"biographie", r"biografía", r"biografia", r"church history",
               r"\bsaint\b", r"reformer", r"theologian", r"伝記", r"전기", r"传记", r"属灵伟人",
               r"教会历史", r"生平"]),
    ("missionary", [r"missionary", r"missionari", r"missionnaire", r"missionário", r"misionero",
                    r"misionaris", r"宣教師", r"선교사", r"mission field", r"church planting",
                    r"宣教", r"差会", r"拓荒", r"植堂"]),
]

CATEGORY_LABELS = {
    "africa": "非洲宣教与见证",
    "china": "中国故事",
    "missionary": "宣教士故事",
    "giant": "属灵伟人",
    "trial": "患难中的信心",
    "lay": "平凡人的见证",
}
REGION_LABELS = ["非洲", "中国", "中东", "亚洲", "拉美", "欧洲", "北美", "大洋洲", "全球"]


def _text_of(article) -> str:
    if isinstance(article, dict):
        parts = [article.get("title", ""), article.get("title_zh", ""),
                 article.get("summary", ""), article.get("summary_zh", ""),
                 (article.get("content") or article.get("content_zh") or "")[:1200]]
    else:
        parts = [article.title or "", article.title_zh or "",
                 article.summary or "", article.summary_zh or "",
                 (article.content or article.content_zh or "")[:1200]]
    return " ".join(str(p) for p in parts)


def _lang_of(article) -> str:
    raw = article.get("language", "en") if isinstance(article, dict) else getattr(article, "language", "en")
    return (raw or "en").lower()[:2]


def _hits(patterns, text: str) -> int:
    return sum(1 for p in patterns if p.search(text))


def score_story(article) -> (int, str):
    """返回 (分数, 判拒理由)。分数 < 阈值即不是故事"""
    text = _text_of(article)
    title = ((article.get("title", "") if isinstance(article, dict) else article.title) or "") + " " + \
            ((article.get("title_zh", "") if isinstance(article, dict) else article.title_zh) or "")
    i18n = _lang_of(article) not in ("en", "zh")

    for p in REJECT_RE:
        if p.search(title):
            return 0, f"标题命中非故事形态：{p.pattern}"

    strong = _hits(STRONG_RE, text)
    medium = _hits(MEDIUM_RE, text)
    narrative = _hits(NARRATIVE_RE, text)
    score = strong * 3 + medium * 2 + narrative

    # 没有正文时（Google News 只给标题+摘要），要求标题本身有故事信号。
    # 非英语标题即使译中前也未必命中「见证 / 生平」这类强信号，
    # 所以允许题材词（missionnaire / missionário / 선교사…）作为信号并补 2 分；
    # 英语 / 中文仍按原来的严格规则，避免把新闻简讯放进来。
    has_body = len((article.get("content") or "") if isinstance(article, dict)
                   else (article.content or article.content_zh or "")) >= 350
    if not has_body:
        if i18n:
            if _hits(STRONG_RE, title) + _hits(MEDIUM_RE, title) == 0:
                return 0, "无正文且标题不是人物故事"
            score += 2
        else:
            if _hits(STRONG_RE, title) == 0:
                return 0, "无正文且标题不是人物故事"
            score += 1

    # 太短的条目不收（避免只剩一句导语）
    if isinstance(article, dict):
        short_len = len((article.get("summary") or "") + (article.get("content") or ""))
    else:
        short_len = len((article.summary or "") + (article.content or ""))
    if short_len < 90 and not has_body:
        return 0, "内容过短"

    return score, ""


def infer_region(article, source_region: str = "") -> str:
    text = _text_of(article) + " " + (source_region or "")
    for name, patterns in REGION_RE:
        if _hits(patterns, text):
            return name
    return source_region or "全球"


def infer_category(article, region: str, fallback: str = "lay") -> str:
    text = _text_of(article)
    for key, patterns in TOPIC_RULES:
        if _hits([re.compile(p, re.IGNORECASE) for p in patterns], text):
            if key == "africa" and region != "非洲":
                continue
            return key
    if region == "非洲":
        return "africa"
    if region == "中国":
        return "china"
    if fallback in CATEGORY_LABELS and fallback != "devotional":
        return fallback
    return "lay"


def infer_tags(article, region: str, category: str) -> List[str]:
    tags: List[str] = []
    text = _text_of(article)
    tag_rules = [
        ("非洲宣教", r"africa|afrique|áfrica|missionary|missionnaire|missionário|misionero|非洲|宣教"),
        ("见证", r"testimony|testemunho|testimonio|témoignage|kesaksian|간증|証し|见证|信主|conversion"),
        ("逼迫", r"persecut|persécut|persegui|persecución|penganiayaan|迫害|박해|逼迫|殉道|集中营"),
        ("孤儿", r"orphan|orphelin|órfão|huérfano|yatim|孤児|고아|孤儿|孩子"),
        ("祷告", r"pray|prier|oração|oración|doa|祈り|기도|祷告"),
        ("复兴", r"revival|réveil|avivamento|kebangunan|リバイバル|부흥|复兴"),
        ("传记", r"biography|biographie|biografia|biografía|伝記|전기|生平|传记"),
        ("医疗", r"hospital|hôpital|clinic|leprosy|病院|병원|医院|麻风"),
        ("译经", r"bible translation|translate|traduction|traducción|译经|翻译圣经"),
        ("家庭", r"family|marriage|famille|família|familia|keluarga|家族|가족|家庭|婚姻"),
    ]
    for label, pat in tag_rules:
        if re.search(pat, text, re.IGNORECASE):
            tags.append(label)
    if region and region not in tags:
        tags.insert(0, region)
    if CATEGORY_LABELS.get(category):
        tags.insert(1 if tags else 0, CATEGORY_LABELS[category])
    extra_tags = (article.get("tags") or [])[:3] if isinstance(article, dict) else (article.tags or [])[:3]
    for t in extra_tags:
        if t and t not in tags:
            tags.append(t)
    return tags[:8]


def _domain(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def filter_and_classify(articles: List[Any], min_score: int = 4,
                        discovered_path: str = "") -> (List[Any], Dict[str, Any]):
    """过滤并归类；返回 (保留条目, 统计信息)"""
    kept = []
    rejected: Dict[str, int] = {}
    domains = set()

    for a in articles:
        score, reason = score_story(a)
        if score < min_score:
            key = reason.split("：")[0]
            rejected[key] = rejected.get(key, 0) + 1
            continue
        if isinstance(a, dict):
            url = a.get("url") or ""
            region = infer_region(a, a.get("region", "") or "")
            category = infer_category(a, region, a.get("category", "") or "")
            a["region"] = region
            a["category"] = category
            a["tags"] = infer_tags(a, region, category)
            extra = dict(a.get("extra") or {})
            extra["story_score"] = score
            extra["domain"] = _domain(url)
            a["extra"] = extra
        else:
            region = infer_region(a, getattr(a, "region", "") or "")
            category = infer_category(a, region, getattr(a, "category", "") or "")
            a.region = region
            a.category = category
            a.tags = infer_tags(a, region, category)
            extra = dict(getattr(a, "extra", None) or {})
            extra["story_score"] = score
            extra["domain"] = _domain(a.url or "")
            a.extra = extra
        if extra["domain"]:
            domains.add(extra["domain"])
        kept.append(a)

    stats = {
        "in": len(articles),
        "kept": len(kept),
        "rejected": rejected,
        "domains": sorted(domains),
    }
    logger.info(f"故事判别：收 {len(kept)}/{len(articles)} 条；拦截原因 {rejected}")

    if discovered_path:
        import os, json
        try:
            old = []
            if os.path.exists(discovered_path):
                with open(discovered_path, "r", encoding="utf-8") as f:
                    old = json.load(f).get("domains", [])
            merged = sorted(set(old) | domains)[:3000]
            os.makedirs(os.path.dirname(discovered_path), exist_ok=True)
            with open(discovered_path, "w", encoding="utf-8") as f:
                json.dump({"count": len(merged), "domains": merged}, f, ensure_ascii=False, indent=1)
        except Exception as e:
            logger.warning(f"写入已发现域名失败：{e}")

    return kept, stats
