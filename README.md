# 基督教世界故事（Christian Story）

每日自动采集**全球范围**关于**宣教士、属灵伟人、平信徒**的属灵小故事，把正文与配图直接摘抄到站内，可作**灵修或讲道参考**。

> 架构与 [基督教世界新闻](https://github.com/jeskuns/christian-news) 同源：每日自动采集、英文标题/摘要云端优先翻译（配额用尽时按需离线翻译）、首页/分类页精选 250 篇、完整列表「查看全部」。本项目的**唯一差异**是定位与 UI——以「故事」为主，直接呈现正文与图片，并采用暖色阅读风。

线上站点：https://christian-story.pages.dev

## 内容分类

| 分类 | 说明 | 示例来源 |
| --- | --- | --- |
| 🌍 宣教士故事 | 跨文化宣教、宣教运动与见证 | Mission Network News、TGC Missions、Desiring God Missions |
| 📖 属灵伟人 | 圣徒传记、教会历史、神学家 | Desiring God / TGC Biographies、Banner of Truth、Challies、5 Minutes |
| 🤝 平信徒见证 | 普通信徒的生命故事与悔改见证 | Revive Our Hearts、I Am Second、Relevant |
| 🕯 灵修小品 | 每日可读的短篇灵修 / 讲道素材 | Desiring God、TGC、Crossway、Our Daily Bread（中英） |

## 功能特性

- **故事直接摘抄**：真实 RSS 源（Desiring God、TGC、Our Daily Bread、Banner of Truth 等）在订阅中即含完整正文，采集时一并抽取，**无需跳转即可在站内阅读**；并自动提取配图。
- **每日自动更新**：GitHub Actions 每天北京时间 08:00 自动采集、生成并发布到 Cloudflare Pages。
- **中文翻译（云端优先 + 离线兜底）**：标题与摘要默认用 MyMemory / Google 免费接口翻译（带本地缓存）；免费配额用尽时，自动在运行时 `pip install argostranslate` 并下载 en→zh 模型，转为本地离线翻译——**不限量、无密钥**。（故事正文为摘抄原文，便于对照阅读；如需全文译中可在 `src/translator.py` 接入付费云翻译。）
- **精选 250**：建库时按「来源优先级 + 新鲜度 + 分类均衡」筛选 250 篇展示于首页/分类页；4 大分类均有基本覆盖。完整列表见首页「查看全部 N 篇」入口（`all.html`）。
- **分类浏览与搜索**：首页分类卡片直达各分类页；分类页支持按标题/正文搜索与按来源筛选。

## 目录结构

```
Christian-story/
├── config/sources.yaml        # 信息源配置（分类 / 解析器 / 关键词）
├── src/
│   ├── models.py              # 数据模型（含 content 正文、image 配图）
│   ├── collector.py           # 采集引擎 + 精选逻辑
│   ├── translator.py          # 标题/摘要译中（云端优先 + 离线 argos 兜底）
│   ├── parsers/
│   │   ├── rss.py             # RSS 解析（抽取正文与配图）
│   │   ├── news_search.py     # 关键词检索（Google News / GDELT 发现）
│   │   └── extract.py         # 文章正文与配图抽取（trafilatura）
│   └── generators/            # 静态站点生成（Jinja2 模板）
├── requirements.txt
└── .github/workflows/deploy.yml
```

## 本地运行

```bash
pip install -r requirements.txt
python run.py full        # 采集 + 生成站点到 site/
python run.py generate    # 仅基于已有数据库生成站点
```

## 增删信息源

编辑 `config/sources.yaml`：

```yaml
  - name: 你的故事源
    url: https://example.com/feed/
    category: giant          # missionary / giant / lay / devotional
    parser: rss              # rss（含正文）或 news_search（关键词发现）
    language: en
    country: US
    max_items: 12
```

- `parser: rss` 的源建议选订阅中带完整正文的站点，体验最佳（直接摘抄）。
- `parser: news_search` 用于全球范围「发现」新故事（Google News / GDELT），以链接形式呈现。

## 部署

仓库已配置 GitHub Actions（`deploy.yml`）：每日定时采集并发布到 Cloudflare Pages 项目 `christian-story`。需仓库 Secrets：`CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID`。

---

*本站为静态聚合示例，故事正文版权归原始来源所有；内容仅供个人灵修与讲道参考，请以官方来源为准。*
