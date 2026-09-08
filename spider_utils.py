# -*- coding: utf-8 -*-
"""通用工具：带重试与随机延时的 GET 请求、未来场次判断。"""

import logging
import random
import time
from datetime import date

import requests

from config import (
    CONNECT_TIMEOUT,
    MAX_RETRIES,
    READ_TIMEOUT,
    REQUEST_INTERVAL,
    RETRY_BACKOFF,
)

logger = logging.getLogger(__name__)


def polite_sleep() -> None:
    """随机延时，模拟人类浏览节奏，控制请求频率。"""
    time.sleep(random.uniform(*REQUEST_INTERVAL))


def get_with_retry(session: requests.Session, url: str, **kwargs):
    """带重试机制的 GET 请求（连接 10s / 读取 30s 超时）。

    Args:
        session: 已配置请求头的 requests.Session。
        url: 请求地址。
        **kwargs: 透传给 session.get 的其他参数。

    Returns:
        成功返回 Response；重试耗尽仍失败返回 None（由调用方决定跳过逻辑）。
    """
    kwargs.setdefault("timeout", (CONNECT_TIMEOUT, READ_TIMEOUT))
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            logger.warning("请求失败（第 %d/%d 次）: %s -> %s",
                           attempt, MAX_RETRIES, url, exc)
            if attempt < MAX_RETRIES:
                time.sleep(attempt * RETRY_BACKOFF)  # 线性退避：2s / 4s
    return None


def is_exam_held(year: int, month: int, today: date | None = None) -> bool:
    """判断某年某月的六级考试是否已举行（约在 6 月中旬 / 12 月中旬）。

    用于自动跳过未来场次（如 2026 年 12 月）。

    Args:
        year: 考试年份。
        month: 考试月份（6 或 12）。
        today: 参照日期，默认取系统当前日期。

    Returns:
        True 表示考试已举行，可以去站点探测真题。
    """
    today = today or date.today()
    # 考试通常在当月中旬，放宽到月初即可认为"当月已到"
    return (year, month) <= (today.year, today.month)
