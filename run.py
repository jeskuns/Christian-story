#!/usr/bin/env python3
"""
基督教故事 · 全球故事搜罗与站点构建

  python run.py            全球搜罗 + 生成站点（默认，等价于 full）
  python run.py full       同上
  python run.py collect    只搜罗与建库，不生成页面
  python run.py generate   离线：只基于现有数据生成站点（不联网）
  python run.py build      generate 的别名
  python run.py validate   校验搜罗故事库字段
  python run.py schedule   启动本机每日定时调度
"""
import os
import sys
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.generators import StorySiteGenerator

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "sources.yaml")
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_DIR = os.path.join(DATA_DIR, "db")
SITE_DIR = os.path.join(BASE_DIR, "site")
TEMPLATE_DIR = os.path.join(BASE_DIR, "src", "generators", "templates")
HEADERS_FILE = os.path.join(BASE_DIR, "_headers")


def make_generator() -> StorySiteGenerator:
    return StorySiteGenerator(SITE_DIR, TEMPLATE_DIR, DB_DIR, HEADERS_FILE)


def generate_only() -> int:
    generator = make_generator()
    problems = generator.validate()
    if problems:
        print("搜罗故事库校验未通过：")
        for p in problems:
            print("  - " + p)
        return 1
    count = generator.generate()
    print(f"完成：{count} 篇故事 → {SITE_DIR}")
    print("本地预览：python -m http.server 8000 -d site")
    return 0


def main():
    parser = argparse.ArgumentParser(description="基督教故事 · 全球故事搜罗")
    parser.add_argument(
        "command", nargs="?", default="full",
        choices=["full", "collect", "generate", "build", "validate", "schedule"],
    )
    parser.add_argument("--workers", type=int, default=8, help="并发采集线程数")
    parser.add_argument("--hour", type=int, default=8, help="本机定时小时")
    parser.add_argument("--minute", type=int, default=30, help="本机定时分钟")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if args.command == "validate":
        generator = make_generator()
        problems = generator.validate()
        if problems:
            for p in problems:
                print("  - " + p)
            return 1
        print("校验通过。")
        return 0

    if args.command in ("generate", "build"):
        return generate_only()

    if args.command == "schedule":
        from src.scheduler import start_scheduler
        start_scheduler(CONFIG_PATH, DATA_DIR, SITE_DIR, TEMPLATE_DIR,
                        hour=args.hour, minute=args.minute)
        return 0

    # full / collect：需要联网搜罗
    from src.collector import Collector
    collector = Collector(CONFIG_PATH, DATA_DIR, workers=args.workers)
    collector.collect()
    collector.save_raw()
    collector.build_database()
    collector.snapshot()
    stats = collector.filter_stats
    print(f"全球搜罗：采到 {stats.get('in', 0)} 条，判别后保留 {stats.get('kept', 0)} 篇真故事，"
          f"发现 {len(stats.get('domains', []))} 个站点域名。")

    if args.command == "collect":
        return 0
    return generate_only()


if __name__ == "__main__":
    sys.exit(main())
