# -*- coding: utf-8 -*-
"""解析器：从真题列表页提取 PDF 链接，并解析出年份、月份、套数等元数据。

站点 URL 规律（2026-09 实测）：
  列表页:  {BASE_URL}/papers/
  PDF 直链: {BASE_URL}/papers/{YYYY}/{MM}/cet6-{YYYY}-{MM}-set-{NN}.pdf
"""

import logging
import re
from dataclasses import dataclass
from urllib.parse import urljoin

from config import PAPERS_INDEX_URL

logger = logging.getLogger(__name__)

# 匹配 PDF 直链：捕获年份、月份（两位数字）、套数（两位数字）
_PDF_PATTERN = re.compile(
    r"/papers/(\d{4})/(\d{2})/cet6-\d{4}-\d{2}-set-(\d{2})\.pdf"
)


@dataclass(frozen=True)
class Paper:
    """一份真题试卷的元数据。"""

    year: int      # 考试年份，如 2023
    month: int     # 考试月份，如 6 或 12
    set_no: int    # 套数，1/2/3
    url: str       # PDF 下载直链

    @property
    def filename(self) -> str:
        """保存文件名，如「2023年6月六级真题_第1套.pdf」。"""
        return f"{self.year}年{self.month}月六级真题_第{self.set_no}套.pdf"


def fetch_pdf_links(session) -> list[str]:
    """抓取真题列表页，提取站内全部 PDF 链接（已去重、转绝对路径）。

    Args:
        session: 已配置请求头的 requests.Session。

    Returns:
        绝对 URL 形式的 PDF 链接列表；列表页请求失败时返回空列表。
    """
    from spider_utils import get_with_retry  # 延迟导入避免循环依赖

    resp = get_with_retry(session, PAPERS_INDEX_URL)
    if resp is None:
        logger.error("真题列表页获取失败: %s", PAPERS_INDEX_URL)
        return []

    # 用 urljoin 统一处理相对/绝对路径（站点 href 以 /cet6-download/ 开头），
    # 去重保持原顺序
    seen, links = set(), []
    for path in re.findall(r'href="([^"]+\.pdf)"', resp.text):
        url = urljoin(resp.url, path)
        if url not in seen:
            seen.add(url)
            links.append(url)
    logger.info("列表页共解析到 %d 个 PDF 链接", len(links))
    return links


def parse_papers(links: list[str], start_year: int, end_year: int) -> list[Paper]:
    """从 PDF 链接中解析元数据，并按年份范围过滤。

    Args:
        links: PDF 绝对链接列表。
        start_year: 起始年份（含）。
        end_year: 结束年份（含）。

    Returns:
        Paper 元数据列表，按年份、月份、套数升序排列。
    """
    papers = []
    for url in links:
        m = _PDF_PATTERN.search(url)
        if not m:
            logger.warning("链接不符合真题命名规则，已过滤: %s", url)
            continue
        year, month, set_no = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if not (start_year <= year <= end_year):
            continue  # 过滤年份范围之外的真题
        papers.append(Paper(year, month, set_no, url))

    papers.sort(key=lambda p: (p.year, p.month, p.set_no))
    logger.info("按 %d-%d 年过滤后剩余 %d 套真题", start_year, end_year, len(papers))
    return papers
