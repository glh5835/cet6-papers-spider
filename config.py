# -*- coding: utf-8 -*-
"""配置文件：年份范围、保存路径、请求头、频率控制等全局参数。"""

from pathlib import Path

# ---------------- 数据源 ----------------
# 主数据源：catteacher0515/cet6-download（GitHub Pages 纯静态站，无需登录）
BASE_URL = "https://catteacher0515.github.io/cet6-download"
PAPERS_INDEX_URL = f"{BASE_URL}/papers/"  # 真题列表页

# ---------------- 保存设置 ----------------
# 真题保存根目录（按 年份/月份/第X套.pdf 结构存放）
SAVE_DIR = Path(r"D:\LEGION D\Documents\英语6级")

# ---------------- 时间范围 ----------------
DEFAULT_START_YEAR = 2023
DEFAULT_END_YEAR = 2026
# 每年考试月份；2026-12 尚未举行，运行时会按当前日期自动跳过未来场次
EXAM_MONTHS = (6, 12)

# ---------------- 请求设置 ----------------
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": PAPERS_INDEX_URL,
}
CONNECT_TIMEOUT = 10   # 连接超时（秒）
READ_TIMEOUT = 30      # 读取超时（秒）
MAX_RETRIES = 3        # 单个文件最大重试次数
RETRY_BACKOFF = 2      # 重试退避基数（秒），第 n 次重试前等待 n * RETRY_BACKOFF

# ---------------- 频率控制（合规：控制请求频率） ----------------
REQUEST_INTERVAL = (1.0, 2.0)   # 每次请求之间随机延时范围（秒）
MAX_WORKERS = 3                 # 并发下载线程数（建议 3-5）

# ---------------- 下载设置 ----------------
CHUNK_SIZE = 256 * 1024         # 分块下载大小（256KB）
MIN_PDF_SIZE = 10 * 1024        # PDF 最小合法体积（10KB），用于校验完整性

# ---------------- 日志 ----------------
LOG_FILE = "cet6_spider.log"
