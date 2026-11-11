"""
每日自动搜罗调度器（APScheduler）
香港时区每日 08:30 执行一次：全球搜罗 → 故事判别 → 译中 → 生成站点
GitHub Actions 另有一条每日 cron，两者可并存（任选其一运行即可）。
"""
import os
import logging
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

from .collector import Collector
from .generators import StorySiteGenerator
from .utils import setup_logging, HK_TZ

logger = logging.getLogger(__name__)


def run_pipeline(config_path: str, data_dir: str, site_dir: str, template_dir: str, workers: int = 8):
    """执行一次完整流程：采集 + 生成站点"""
    logger.info("=" * 50)
    logger.info("Daily global story collection started")
    start = datetime.now(HK_TZ)

    collector = Collector(config_path, data_dir, workers=workers)
    collector.collect()
    collector.save_raw()
    collector.build_database()
    snap = collector.snapshot()

    generator = StorySiteGenerator(
        site_dir=site_dir,
        template_dir=template_dir,
        db_dir=os.path.join(data_dir, "db"),
        headers_file=os.path.join(os.path.dirname(data_dir), "_headers"),
    )
    generator.generate()

    elapsed = (datetime.now(HK_TZ) - start).total_seconds()
    stats = collector.filter_stats
    logger.info(
        f"Pipeline finished in {elapsed:.1f}s: collected {stats.get('in', 0)}, "
        f"kept {stats.get('kept', 0)} stories, errors {len(snap.errors)}"
    )
    if collector.zero_sources:
        logger.warning(f"空源 {len(collector.zero_sources)} 个（需检查 feed 地址或检索词）: "
                       + ", ".join(collector.zero_sources))
    logger.info("=" * 50)
    return snap


def start_scheduler(config_path: str, data_dir: str, site_dir: str, template_dir: str, hour: int = 8, minute: int = 30):
    """启动每日定时调度"""
    setup_logging()
    scheduler = BlockingScheduler(timezone=HK_TZ)
    scheduler.add_job(
        run_pipeline,
        "cron",
        hour=hour,
        minute=minute,
        args=(config_path, data_dir, site_dir, template_dir),
        id="daily_story_collection",
        replace_existing=True,
    )
    logger.info(f"Scheduler started, will run daily at {hour:02d}:{minute:02d} (Asia/Hong_Kong)")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")
