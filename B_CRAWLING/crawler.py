# B_CRAWLING/crawler.py
import csv
import logging
import os
import random
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any

import pandas as pd

from B_CRAWLING.config import NuriConfig
from B_CRAWLING.http_client import NuriHttpClient
from B_CRAWLING.mapper import BID_FULL_NO_COLUMN, build_bid_id, to_standard_record

logger = logging.getLogger(__name__)


class CsvWriter:
    def __init__(self, path: str):
        # CSV 파일 경로를 설정하고 기존 헤더 존재 여부를 확인
        self.path = path
        self._header_written = os.path.exists(path)

    def append(self, record: dict):
        # 레코드 1건을 CSV 파일에 append (헤더는 최초 1회만 작성)
        with open(self.path, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=record.keys())
            if not self._header_written:
                writer.writeheader()
                self._header_written = True
            writer.writerow(record)


class NuriBidCrawler:
    def __init__(self, cfg: NuriConfig):
        # 크롤러 기본 구성 요소 초기화 (설정, HTTP, CSV, 체크포인트)
        self.cfg = cfg
        self.http = NuriHttpClient(cfg)
        self.writer = CsvWriter(cfg.output_csv)
        self._ckpt_dir = Path(cfg.checkpoint_dir)
        self._ckpt_dir.mkdir(parents=True, exist_ok=True)
        self._ckpt_path = self._ckpt_dir / cfg.checkpoint_file

    def export_excel(self, path: str) -> None:
        # 누적된 CSV 결과를 엑셀 파일로 변환하여 저장
        csv_path = Path(self.cfg.output_csv)
        if not csv_path.exists():
            return
        try:
            df = pd.read_csv(csv_path, encoding="utf-8-sig")
            if df.empty:
                return
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            df.to_excel(path, index=False, engine="openpyxl")
            logger.info("엑셀 내보내기 완료: %s", path)
        except Exception as e:
            logger.warning("엑셀 내보내기 실패: %s", e)

    def _sleep_normal(self):
        # 서버 부하 방지를 위한 기본 + 랜덤 지연 시간 대기
        base = self.cfg.base_sleep_sec
        jitter = random.uniform(*self.cfg.jitter_sec)
        time.sleep(base + jitter)

    def _read_ckpt(self) -> Dict[str, Any]:
        # 체크포인트 파일을 읽어 마지막 수집 상태를 복원
        if not self._ckpt_path.exists():
            return {"version": 1, "keywords": {}}
        try:
            with open(self._ckpt_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return {"version": 1, "keywords": {}}
            data.setdefault("version", 1)
            data.setdefault("keywords", {})
            if not isinstance(data["keywords"], dict):
                data["keywords"] = {}
            return data
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("체크포인트 읽기 실패, 새로 시작: %s", e)
            return {"version": 1, "keywords": {}}

    def _atomic_write_json(self, path: Path, data: Dict[str, Any]) -> None:
        # 체크포인트 JSON을 원자적으로 안전하게 저장
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

    def _load_start_page(self, keyword: str, default: int = 1) -> int:
        # 키워드별로 마지막에 저장된 다음 시작 페이지를 조회
        data = self._read_ckpt()
        kw = (keyword or "").strip()
        kw_state = data["keywords"].get(kw, {})
        page = kw_state.get("next_page", default)
        try:
            page = int(page)
        except Exception:
            page = default
        return max(1, page)

    def _save_next_page(self, keyword: str, next_page: int) -> None:
        # 키워드별 다음에 수집할 페이지 번호를 체크포인트에 저장
        data = self._read_ckpt()
        kw = (keyword or "").strip()
        data["keywords"].setdefault(kw, {})
        data["keywords"][kw]["next_page"] = int(next_page)
        data["keywords"][kw]["updated_at"] = int(time.time())
        self._atomic_write_json(self._ckpt_path, data)

    def _load_saved_bid_set(self, tail_bytes: int = 512 * 1024) -> set:
        # 이미 CSV에 저장된 bid 번호들을 중복 방지용으로 로드
        path = Path(self.cfg.output_csv)
        if not path.exists():
            return set()
        seen = set()
        try:
            with open(path, "rb") as f:
                f.seek(0, 2)
                size = f.tell()
                if size == 0:
                    return set()
                read_from = max(0, size - tail_bytes)
                f.seek(read_from)
                if read_from > 0:
                    f.readline()
                tail = f.read().decode("utf-8-sig", errors="ignore")
            lines = tail.splitlines()
            with open(path, "r", newline="", encoding="utf-8-sig") as f:
                header = next(csv.reader(f))
                if BID_FULL_NO_COLUMN not in header:
                    return set()
                col_idx = header.index(BID_FULL_NO_COLUMN)
            for line in lines:
                row = next(csv.reader([line]), None)
                if row and len(row) > col_idx:
                    v = (row[col_idx] or "").strip()
                    if v:
                        seen.add(v)
        except (OSError, UnicodeDecodeError) as e:
            logger.debug("저장된 bid 집합 로드 생략: %s", e)
        return seen

    def crawl_once(
        self,
        keyword: str,
        max_pages: Optional[int] = None,
        start_page: int = 1,
    ) -> int:
        # 키워드 기준으로 입찰 목록/상세를 순회하며 한 번 수집 실행
        collected = 0

        if start_page == 1:
            page = self._load_start_page(keyword, default=1)
        else:
            page = start_page

        saved_bids = self._load_saved_bid_set()
        pages_done = 0
        logger.info("키워드=%r, 시작 페이지=%d (재개 시 이어서 수집)", keyword or "(전체)", page)

        while True:
            if max_pages is not None and pages_done >= max_pages:
                break

            try:
                rows = self.http.fetch_list(page=page, keyword=keyword)
            except Exception as e:
                logger.warning("목록 조회 실패(page=%d). 재실행 시 이어서 수집 가능: %s", page, e)
                self._save_next_page(keyword, page)
                break

            if not rows:
                self._save_next_page(keyword, page)
                break

            for row in rows:
                try:
                    detail = self.http.fetch_detail(row)
                    record = to_standard_record(row, detail)
                    bid_full = (record.get(BID_FULL_NO_COLUMN) or "").strip()
                    if bid_full and bid_full in saved_bids:
                        self._sleep_normal()
                        continue
                    self.writer.append(record)
                    if bid_full:
                        saved_bids.add(bid_full)
                    collected += 1
                except Exception as e:
                    logger.debug("행 처리 스킵: %s", e)
                finally:
                    self._sleep_normal()

            pages_done += 1
            logger.info("페이지 %d 완료, 이번 키워드 누적 %d건", page, collected)

            next_row_yn = rows[-1].get("nextRowYn")
            if str(next_row_yn).upper() != "Y":
                self._save_next_page(keyword, page + 1)
                break

            self._save_next_page(keyword, page + 1)
            page += 1

        logger.info("키워드=%r 수집 완료, 총 %d건", keyword or "(전체)", collected)
        return collected
