# -*- coding: utf-8 -*-
"""下载器：支持断点续传、完整性校验、并发批量下载。

下载策略：
  - 已存在合法 PDF -> 跳过（实现"已下载自动跳过"）
  - 存在 .part 半成品 -> 发送 Range 请求头从断点续传
  - 下载完成后校验体积与 Content-Type，防止把 404 页面存成 PDF
"""

import logging
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

from config import (
    CHUNK_SIZE,
    CONNECT_TIMEOUT,
    HEADERS,
    MAX_RETRIES,
    MAX_WORKERS,
    MIN_PDF_SIZE,
    READ_TIMEOUT,
    RETRY_BACKOFF,
)
from parser import Paper
from spider_utils import polite_sleep

logger = logging.getLogger(__name__)


def _target_path(paper: Paper, save_dir: Path) -> Path:
    """按「年份/月份/2023年6月六级真题_第1套.pdf」结构生成保存路径。"""
    return save_dir / str(paper.year) / f"{paper.month:02d}" / paper.filename


def _looks_like_pdf(resp: requests.Response) -> bool:
    """校验响应内容是否为合法 PDF（类型或魔数 %PDF-）。"""
    ctype = resp.headers.get("Content-Type", "").lower()
    if "pdf" in ctype:
        return True
    head = resp.raw.read(5, cache_content=True) if resp.raw else b""
    return head.startswith(b"%PDF-")


def download_pdf(session: requests.Session, paper: Paper, save_dir: Path) -> bool:
    """下载单份真题 PDF（含跳过、续传、重试、校验）。

    Args:
        session: 已配置请求头的 requests.Session。
        paper: 真题元数据。
        save_dir: 保存根目录。

    Returns:
        True 表示下载成功（或本地已存在）；False 表示失败。
    """
    path = _target_path(paper, save_dir)

    # 已存在且体积合法 -> 视为完成，自动跳过
    if path.exists() and path.stat().st_size >= MIN_PDF_SIZE:
        logger.info("已存在，跳过: %s", path)
        return True

    part_path = path.with_suffix(path.suffix + ".part")
    downloaded = part_path.stat().st_size if part_path.exists() else 0

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            headers = dict(HEADERS)
            if downloaded:
                headers["Range"] = f"bytes={downloaded}-"
                logger.info("断点续传 %s（已有 %d 字节）", paper.filename, downloaded)

            resp = session.get(
                paper.url,
                headers=headers,
                stream=True,
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )
            # 服务器不支持 Range（返回 200 全量）时从头写
            mode = "ab" if (downloaded and resp.status_code == 206) else "wb"
            if mode == "wb":
                downloaded = 0

            if not _looks_like_pdf(resp):
                logger.warning("响应不是 PDF（可能未上线）: %s -> HTTP %s",
                               paper.url, resp.status_code)
                return False

            resp.raise_for_status()
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(part_path, mode) as f:
                for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

            # 完整性校验：体积过小视为损坏
            if part_path.stat().st_size < MIN_PDF_SIZE:
                logger.warning("文件体积异常（<%d 字节），丢弃重下: %s",
                               MIN_PDF_SIZE, paper.filename)
                part_path.unlink(missing_ok=True)
                downloaded = 0
                continue

            os.replace(part_path, path)  # 校验通过才落正式文件名
            logger.info("下载成功: %s（%.1f KB）", path, path.stat().st_size / 1024)
            return True

        except requests.RequestException as exc:
            downloaded = part_path.stat().st_size if part_path.exists() else 0
            logger.warning("下载失败（第 %d/%d 次）: %s -> %s",
                           attempt, MAX_RETRIES, paper.filename, exc)
            if attempt < MAX_RETRIES:
                time.sleep(attempt * RETRY_BACKOFF)
        except OSError as exc:
            logger.error("本地文件读写错误: %s -> %s", path, exc)
            return False

    logger.error("重试耗尽，下载失败: %s", paper.filename)
    return False


def batch_download(session: requests.Session, papers: list[Paper],
                   save_dir: Path) -> tuple[int, int]:
    """并发批量下载（默认 3 线程），线程内随机延时控制频率。

    Args:
        session: 已配置请求头的 requests.Session。
        papers: 待下载真题列表。
        save_dir: 保存根目录。

    Returns:
        (成功数, 失败数)。已存在的文件计入成功。
    """
    success = fail = 0

    def _task(paper: Paper) -> bool:
        polite_sleep()  # 每个任务启动前随机延时 1-2 秒，避免瞬时并发过高
        return download_pdf(session, paper, save_dir)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_task, p): p for p in papers}
        for future in as_completed(futures):
            paper = futures[future]
            try:
                if future.result():
                    success += 1
                else:
                    fail += 1
            except Exception:  # 兜底：任何线程内异常都不影响整体流程
                logger.exception("任务异常: %s", paper.filename)
                fail += 1
            # 线程池空闲间隙也加一点随机间隔
            time.sleep(random.uniform(0.2, 0.6))

    return success, fail
