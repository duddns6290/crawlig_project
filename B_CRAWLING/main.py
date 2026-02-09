# B_CRAWLING/main.py
import argparse
import logging
import time
from typing import List, Optional

from B_CRAWLING.config import NuriConfig
from B_CRAWLING.crawler import NuriBidCrawler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


def run_interval(
    crawler: NuriBidCrawler,
    keywords: List[str],
    interval_sec: int,
    max_pages: Optional[int],
    export_file: str,
):
    while True:
        for kw in keywords:
            crawler.crawl_once(keyword=kw, max_pages=max_pages)
        crawler.export_excel(export_file)
        time.sleep(interval_sec)


def main():
    p = argparse.ArgumentParser(
        description="Nuri bid crawler (list -> detail) with resume/dedupe/retry/export"
    )
    p.add_argument(
        "--cookie",
        required=True,
        help="누리장터 로그인 후 F12 > 네트워크 > 목록 조회 요청에서 Cookie 헤더 값 복사",
    )
    p.add_argument(
        "--mode",
        choices=["once", "interval"],
        default="once",
        help="실행 모드",
    )
    p.add_argument(
        "--interval-sec",
        type=int,
        default=3600,
        help="interval 모드 주기(초)",
    )
    p.add_argument(
        "--keyword",
        action="append",
        default=[""],
        help="검색 키워드(공고명). 여러 개면 --keyword 여러 번",
    )
    p.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="테스트용: 최대 몇 페이지까지 수집할지 제한",
    )
    p.add_argument(
        "--export",
        default="bids_export.xlsx",
        help="엑셀 내보내기 파일명",
    )
    args = p.parse_args()

    cfg = NuriConfig(cookie=args.cookie)
    crawler = NuriBidCrawler(cfg)

    if args.mode == "once":
        for kw in args.keyword:
            crawler.crawl_once(keyword=kw, max_pages=args.max_pages)
        crawler.export_excel(args.export)
    else:
        run_interval(
            crawler=crawler,
            keywords=args.keyword,
            interval_sec=args.interval_sec,
            max_pages=args.max_pages,
            export_file=args.export,
        )


if __name__ == "__main__":
    main()
