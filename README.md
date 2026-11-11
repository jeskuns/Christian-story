# 基督教故事（Christian Story）

**从全世界的网站，自动搜罗真正发生过的生命故事。**

不是新闻简讯，不是书评书摘，不是灵修小品，也不是书籍介绍——是宣教士的跋涉、非洲村落与部落里的教会、战火中不丢下一个孩子的坚持、逼迫下仍然不恨的人、普通人悔改的那一天。可以是最新的，也可以是几十年前的老故事；不必追新，但也不排斥最新。用户点名要的「马背上的讲道者」「艾伟德」「剑桥七杰」这类经典，以及**非洲宣教故事**，都在搜罗范围内。

线上站点：https://christian-story.pages.dev

> 方向：本项目是**自动搜罗站**，不是人工写故事的站。每天从全球多语种、多地区的网站广撒网，抓到候选后由故事判别器筛掉不算故事的东西，再译成中文、补回全文、生成独立阅读页。站内全部内容均为搜罗结果，不含人工编写或整理的篇目。

## 每日流程

```
全球源（直连 RSS + Google News 各地区版位 + GDELT）
   → 去重 → 故事判别（挡掉新闻/书评/灵修/神学/活动…）
   → 解出原文直链、补抓全文 → 标题/摘要/正文译中
   → 合并入库（按采集时间保留 365 天）→ 生成静态站 → Cloudflare Pages
```

- **故事判别**：`src/story_filter.py` 按人物叙事、生平时间线、见证 / 传记 / 宣教 / 患难等特征打分；标题命中「书评、每日灵修、讲章、快讯、播客、报名、募捐、观点…」直接丢弃。低于阈值不进库。
- **地区自动判别**：非洲、中国、中东、亚洲、拉美、欧洲、北美、大洋洲、全球，可单独浏览与搜索。
- **主题自动分类**：中国故事 / 非洲宣教与见证 / 宣教士故事 / 属灵伟人 / 患难中的信心 / 平凡人的见证。
- **长期保留**：按「采集时间」保留一年，不因文章发表日期旧而丢弃；经典老故事不会被滚动替换。
- **域名发现**：每天把新触达的站点域名写进 `data/db/discovered_domains.json`，用于持续扩源。

## 搜罗范围

| 类型 | 覆盖 |
| --- | --- |
| 直连全文订阅 | 跨洲的见证、宣教、教会历史、受逼迫教会站点（I Am Second、Mission Network News、IMB、Assist News、TGC、Desiring God、Banner of Truth、Christianity Today、Christian Post、VOM、Wycliffe 等） |
| Google News 地区版位 | 非洲（尼日利亚 / 肯尼亚 / 南非 / 加纳 / 法语非洲 / 葡语非洲）、中国与华人（大陆 / 台湾 / 香港）、亚洲（印度 / 韩国 / 日本 / 印尼 / 菲律宾）、中东、拉美（巴西 / 墨西哥 / 亚马逊）、欧洲（英国 / 法国 / 乌克兰）、北美、大洋洲 |
| 语言 | 英、中、法、葡、西、日、韩、印尼等 |
| GDELT 全球文档库 | 返回原文直链，作为 Google 之外的兜底，可直接抓正文 |

源清单见 `config/sources.yaml`。**加一个源**：照抄一段，改 `name` / `country` / `language` / `extra.query` 即可，第二天自动生效。

## 站点结构

```
site/
├── index.html                 首页：先读这几篇 / 最新搜罗 / 按地区 / 六大主题书架
├── latest.html                最新搜罗（按发布时间倒序）
├── regions.html               按地区分架（非洲、中国、中东、拉美…）
├── all.html                   全部故事（按主题）
├── categories/<key>.html      6 个主题分类页
├── story/<id>.html            每篇故事的独立阅读页
├── about.html                 搜罗说明、判别规则、已发现域名
├── sources.html               旧链接兼容跳转
└── assets/                    CSS（含 7 套配色）与 JS（搜索 / 标签 / 地区 / 配色）
```

搜罗故事的阅读页包含：原文标题、来源网站、发布日期、地区、译文正文、机翻提示、原文链接与同主题推荐。

## 本地运行

```bash
pip install -r requirements.txt

python run.py              # 全球搜罗 + 建库 + 生成站点（默认，需联网）
python run.py full         # 同上
python run.py collect      # 只搜罗与建库，不生成页面
python run.py generate     # 离线：用现有数据重建站点（不联网）
python run.py build        # generate 的别名
python run.py validate     # 校验搜罗故事库字段
python run.py schedule     # 本机每日 08:30 定时搜罗（APScheduler）

python -m http.server 8000 -d site   # 本地预览
```

Windows 可用 `update.bat` 一键搜罗 + 构建。

## 目录结构

```
Christian-story/
├── config/sources.yaml          ★ 全球故事源清单（地区 / 语言 / 检索词）
├── src/
│   ├── collector.py             ★ 采集引擎：并发、去重、判别、补抓、翻译、建库
│   ├── story_filter.py          ★ 故事判别、地区与主题归类
│   ├── translator.py            ★ 多语言译中（云端 + argos 离线 + 缓存）
│   ├── models.py / utils.py     数据模型与工具
│   ├── parsers/                 RSS / 检索 / 正文抽取
│   └── generators/
│       ├── story_site.py        ★ 读取搜罗库，生成全站
│       └── templates/           ★ Jinja2 模板
├── data/
│   ├── db/articles.json         ★ 搜罗故事库（每日更新）
│   ├── db/discovered_domains.json / filter_stats.json
│   ├── raw/                     每日原始采集归档
│   └── translation_cache.json   译文缓存
├── site/                        ★ 部署产物
├── _headers                     Pages 响应头（构建时复制进 site/）
└── .github/workflows/deploy.yml 每日 cron 搜罗 + 部署 + 回推
```

## 部署

GitHub Actions `deploy.yml`：

- **每日 UTC 20:00（北京时间次日 04:00）**：跑 `python run.py full --workers 8`，全球搜罗 → 生成 → `wrangler pages deploy` → 把新故事与译文缓存回推 `master`。
- **push 到 master**（改动涉及源配置 / 模板 / 样式 / 构建脚本）：库里已有判别通过的故事时，只跑 `python run.py generate` 离线重建并部署，不重复采集；库为空（例如首次上线）则先跑一次完整搜罗再部署，避免把 0 篇空站推上线。
- **手动 workflow_dispatch**：立即跑一次完整搜罗。

Pages 项目名 `christian-story`，需仓库 Secrets：`CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID`。本机也可用已缓存的 `wrangler` 凭据直接 `wrangler pages deploy site --project-name=christian-story`。

> **网络说明**：Google News 在中国大陆网络常不可达，本机跑 `python run.py full` 基本抓不到东西，这是正常的；采集一律由 GitHub Actions 的美国 IP 完成。改完代码直接 `git push origin master` 即可，CI 会自动搜罗并发布；想立刻重跑一次，到 Actions 手动 `Run workflow`（`workflow_dispatch`）。首次搜罗之前，首页会显示一条「等待首次运行」的提示，不会出现一堆 0。

> **本机 Python 版本**：若本机 Python 较新（如 3.15）没有 `pyyaml` 预编译包，`pip install -r requirements.txt` 会卡在编译。`src/config_loader.py` 已内置零依赖的 YAML 子集解析兜底，只装 `requests / feedparser / beautifulsoup4 / jinja2` 也能跑离线构建与采集。CI 用 Python 3.12，无此问题。

## 翻译与版权

英、法、葡、西、日、韩、印尼语的故事由免费接口（MyMemory / Google）或本地离线模型自动译成中文：短文本直走云端，英文长正文走 argos 离线，其它语言长正文按句切块走云端；中文文章跳过翻译。翻译失败时保留原文，绝不阻塞采集，并有接口失败熔断避免拖慢整轮任务。词句可能生硬，**未作人工改写**。正文版权归原作者与原始网站所有，每篇都附原始网站名称与原文链接；引用请以原文为准。本站只作索引、翻译与阅读呈现，内容仅供个人阅读、灵修与讲道参考。
