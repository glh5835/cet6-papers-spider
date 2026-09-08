# -*- coding: utf-8 -*-
"""入口脚本。

用法：
    pip install -r requirements.txt
    python main.py                   # 爬取全部默认年份（2023-2026）
    python main.py --start 2023 --end 2026
    python main.py --start 2025      # 只爬 2025 年至今
"""

import argparse
import logging
import sys
from pathlib import Path

from config import LOG_FILE, SAVE_DIR

# 日志：控制台 + 文件双输出
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="大学英语六级真题 PDF 爬虫")
    parser.add_argument("--start", type=int, default=2023,
                        help="起始年份（含），默认 2023")
    parser.add_argument("--end", type=int, default=2026,
                        help="结束年份（含），默认 2026")
    parser.add_argument("--save-dir", type=Path, default=SAVE_DIR,
                        help="保存根目录，默认 %(default)s")
    return parser.parse_args()


def main() -> int:
    """程序入口：校验参数 -> 运行爬虫 -> 返回退出码。"""
    args = parse_args()
    if args.start > args.end:
        logger.error("起始年份不能大于结束年份")
        return 1

    # 确保项目目录在 sys.path 中（支持从任意工作目录运行）
    sys.path.insert(0, str(Path(__file__).resolve().parent))

    from spider import CET6Spider

    spider = CET6Spider(start_year=args.start, end_year=args.end,
                        save_dir=args.save_dir)
    success, fail = spider.run()
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
