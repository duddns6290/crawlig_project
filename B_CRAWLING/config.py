from dataclasses import dataclass
from typing import Tuple
from datetime import date, timedelta
from pathlib import Path
import os


def ymd(d: date) -> str:
    return d.strftime("%Y%m%d")


TODAY = date.today()

PROJECT_ROOT = Path(__file__).resolve().parent

DEFAULT_CHECKPOINT_DIR = Path(
    os.getenv("B_CRAWLING_CHECKPOINT_DIR", str(PROJECT_ROOT / "checkpoints"))
)

@dataclass
class NuriConfig:
    # endpoints
    list_url: str = "https://nuri.g2b.go.kr/nn/nnb/nnba/selectBidPbancList.do"
    detail_url: str = "https://nuri.g2b.go.kr/nn/nnb/nnbb/selectBidPbancPrgsDetl.do"

    # headers
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
    )
    origin: str = "https://nuri.g2b.go.kr"
    referer: str = "https://nuri.g2b.go.kr/"
    cookie: str = ""

    # 화면 식별 헤더
    list_menu_info: str = '{"menuNo":"15401","menuCangVal":"NNBA001_01","bsneClsfCd":"%EC%97%85130031","scrnNo":"00777"}'
    list_submissionid: str = "mf_wfm_container_selectBidPbancList"
    detail_menu_info: str = '{"menuNo":"12062","menuCangVal":"NNBB001_01","bsneClsfCd":"%EC%97%85130031","scrnNo":"01978"}'
    detail_submissionid: str = "mf_wfm_container_selectBidPbancDetl"

    record_count_per_page: str = "10"

    # 공고 게시일: 오늘 기준 최근 30일
    pbanc_pstg_st_dt: str = ymd(TODAY - timedelta(days=30))
    pbanc_pstg_ed_dt: str = ymd(TODAY)

    # 개찰일: 오늘 ~ 30일 후
    onbs_prnmnt_st_dt: str = ymd(TODAY)
    onbs_prnmnt_ed_dt: str = ymd(TODAY + timedelta(days=30))

    pbanc_pstg_yn: str = "Y"

    # 안정성 옵션
    timeout_sec: int = 15
    max_retries: int = 5
    base_sleep_sec: float = 0.8
    jitter_sec: Tuple[float, float] = (0.2, 0.8)
    html_block_backoff: Tuple[int, int, int] = (10, 20, 40)

    # 출력
    output_csv: str = "result.csv"

    # checkpoint
    checkpoint_dir: str = str(DEFAULT_CHECKPOINT_DIR)
    checkpoint_file: str = "crawl_state.json"