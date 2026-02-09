import random
import time
from typing import Any, Dict, List
import requests
from B_CRAWLING.config import NuriConfig


class NuriHttpClient:
    def __init__(self, cfg: NuriConfig):
        self.cfg = cfg
        self.session = requests.Session()

    def _common_headers(self) -> Dict[str, str]:
        return {
            "accept": "application/json",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "content-type": "application/json;charset=UTF-8",
            "origin": self.cfg.origin,
            "referer": self.cfg.referer,
            "user-agent": self.cfg.user_agent,
            "cookie": self.cfg.cookie,
            "usr-id": "null",
        }

    def _list_headers(self) -> Dict[str, str]:
        h = self._common_headers()
        h.update({
            "menu-info": self.cfg.list_menu_info,
            "submissionid": self.cfg.list_submissionid,
        })
        return h

    def _detail_headers(self) -> Dict[str, str]:
        h = self._common_headers()
        h.update({
            "menu-info": self.cfg.detail_menu_info,
            "submissionid": self.cfg.detail_submissionid,
        })
        return h

    def post_json(self, url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> Dict[str, Any]:
        html_fail_count = 0

        for attempt in range(1, self.cfg.max_retries + 1):
            try:
                resp = self.session.post(
                    url, headers=headers, json=payload, timeout=self.cfg.timeout_sec
                )
                resp.raise_for_status()

                # HTML 차단 감지
                txt = (resp.text or "")
                if txt[:200].lower().find("<html") != -1:
                    html_fail_count += 1
                    idx = min(html_fail_count, len(self.cfg.html_block_backoff)) - 1
                    sleep_s = self.cfg.html_block_backoff[idx]
                    time.sleep(sleep_s)
                    if html_fail_count >= 3:
                        raise RuntimeError("연속 HTML 응답(3회). 쿠키/세션/차단 상태를 확인하세요.")
                    continue

                ct = (resp.headers.get("Content-Type") or "").lower()
                if "application/json" not in ct:
                    snippet = txt[:200].replace("\n", " ")
                    raise RuntimeError(f"Non-JSON 응답. Content-Type={ct}, snippet={snippet}")

                return resp.json()

            except Exception as e:
                wait = min(2 ** attempt, 16) + random.uniform(0, 1.0)
                time.sleep(wait)

        raise RuntimeError("최대 재시도 초과")

    def fetch_list(self, page: int, keyword: str = "") -> List[Dict[str, Any]]:
        payload = {
            "dlParamM": {
                "bidPbancNo": "",
                "bidPbancOrd": "",
                "bidPbancNm": keyword or "",
                "prcmBsneSeCd": "",
                "bidPbancPgstCd": "",
                "bidMthdCd": "",
                "frgnrRprsvYn": "",
                "kbrdrId": "",
                "pbancInstUntyGrpNo": "",
                "pbancKndCd": "",
                "pbancSttsCd": "",
                "pdngYn": "",
                "scsbdMthdCd": "",
                "stdCtrtMthdCd": "",
                "untyGrpNo": "",
                "usrTyCd": "",

                "pbancPstgStDt": self.cfg.pbanc_pstg_st_dt,
                "pbancPstgEdDt": self.cfg.pbanc_pstg_ed_dt,
                "onbsPrnmntStDt": self.cfg.onbs_prnmnt_st_dt,
                "onbsPrnmntEdDt": self.cfg.onbs_prnmnt_ed_dt,
                "pbancPstgYn": self.cfg.pbanc_pstg_yn,
                "currentPage": page,
                "recordCountPerPage": self.cfg.record_count_per_page,
                "rowNum": "",
            }
        }

        data = self.post_json(self.cfg.list_url, self._list_headers(), payload)
        if data.get("ErrorCode") != 0:
            raise RuntimeError(f"List Error: {data.get('ErrorMsg')} ({data.get('ErrorCode')})")

        result = data.get("result", [])
        if not isinstance(result, list):
            raise RuntimeError("목록 응답 구조가 예상과 다릅니다: result가 list가 아님")

        return result

    def fetch_detail(self, row: Dict[str, Any]) -> Dict[str, Any]:
        # 상세 조회
        bidPbancNo = str(row.get("bidPbancNo", ""))
        bidPbancOrd = str(row.get("bidPbancOrd", ""))
        bidClsfNo = str(row.get("bidClsfNo", ""))
        bidPrgrsOrd = str(row.get("bidPrgrsOrd", ""))

        payload = {
            "dlSrchCndtM": {
                "pbancFlag": "",
                "bidPbancNo": bidPbancNo,
                "bidPbancOrd": bidPbancOrd,
                "bidClsfNo": bidClsfNo,
                "bidPrgrsOrd": bidPrgrsOrd,
                "bidPbancNm": "",
                "bidPbancPgstCd": "",
                "flag": "",
                "frgnrRprsvYn": "",
                "kbrdrId": "",
                "odn3ColCn": "",
                "paramGbn": "1",
                "pbancInstUntyGrpNo": "",
                "pbancPstgEdDt": "",
                "pbancPstgStDt": "",
                "prcmBsneSeCd": "",
                "pstNo": bidPbancNo,
                "recordCountPerPage": "",
                "rowNum": "",
                "untyGrpNo": "",
            }
        }

        data = self.post_json(self.cfg.detail_url, self._detail_headers(), payload)
        if data.get("ErrorCode") != 0:
            raise RuntimeError(f"Detail Error: {data.get('ErrorMsg')} ({data.get('ErrorCode')})")

        result = data.get("result", {})
        if not isinstance(result, dict):
            raise RuntimeError("상세 응답 구조가 예상과 다릅니다: result가 dict가 아님")

        return result
