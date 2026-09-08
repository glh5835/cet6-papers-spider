# -*- coding: utf-8 -*-
"""主爬虫逻辑：协调解析与下载，按年份/月份场次组织任务。"""

import logging

import requests

import config
from downloader import batch_download
from parser import fetch_pdf_links, parse_papers
from spider_utils import get_with_retry, is_exam_held, polite_sleep

logger = logging.getLogger(__name__)


class CET6Spider:
    """六级真题爬虫。

    Attributes:
        start_year: 起始年份（含）。
        end_year: 结束年份（含）。
        save_dir: 保存根目录。
    """

    def __init__(self, start_year: int = config.DEFAULT_START_YEAR,
                 end_year: int = config.DEFAULT_END_YEAR,
                 save_dir=config.SAVE_DIR):
        self.start_year = start_year
        self.end_year = end_year
        self.save_dir = save_dir
        self.session = requests.Session()
        self.session.headers.update(config.HEADERS)

    def fetch_paper_list(self, year: int, month: int) -> None:
        """获取某年某月的真题列表（演示用占位）。

        实际实现中列表为全站一页式（PAPERS_INDEX_URL），此处保留接口
        以便站点结构变化时替换为按场次抓取的版本。
        """
        url = f"{config.BASE_URL}/papers/{year}/{month:02d}/"
        resp = get_with_retry(self.session, url)
        if resp is not None:
            logger.info("场次 %d年%d月 列表页可达", year, month)

    def run(self) -> tuple[int, int]:
        """主运行逻辑：解析列表 -> 过滤年份 -> 并发下载。

        Returns:
            (成功数, 失败数)。
        """
        self.save_dir.mkdir(parents=True, exist_ok=True)
        logger.info("开始爬取 %d-%d 年六级真题 -> %s",
                    self.start_year, self.end_year, self.save_dir)

        papers = parse_papers(fetch_pdf_links(self.session),
                              self.start_year, self.end_year)
        if not papers:
            logger.error("未解析到任何目标年份的真题，请检查站点结构是否变更")
            return 0, 0

        # 逐场次过滤：已举行的考试才去探测（自动跳过 2026-12 等未来场次）
        downloadable = []
        for paper in papers:
            polite_sleep()
            if is_exam_held(paper.year, paper.month):
                downloadable.append(paper)
            else:
                logger.info("考试尚未举行，跳过: %d年%d月 第%d套",
                            paper.year, paper.month, paper.set_no)

        logger.info("待下载 %d 套真题", len(downloadable))
        success, fail = batch_download(self.session, downloadable, self.save_dir)
        logger.info("===== 完成：成功 %d 套，失败 %d 套 =====", success, fail)
        return success, fail
