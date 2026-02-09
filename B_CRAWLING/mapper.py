from datetime import datetime
from typing import Any, Dict
import html

BID_FULL_NO_COLUMN = "입찰공고번호(Full)"


def unescape_html(s):
    # HTML 이스케이프 문자열을 원문으로 복원
    if s is None:
        return s
    return html.unescape(str(s))


def build_bid_id(row: Dict[str, Any]) -> str:
    # 입찰공고번호 + 차수로 내부용 입찰 ID 생성
    return f"{row.get('bidPbancNo','')}-{row.get('bidPbancOrd','')}"


def safe_dict(x: Any) -> Dict[str, Any]:
    # dict가 아니면 빈 dict로 치환
    return x if isinstance(x, dict) else {}


def safe_list(x: Any) -> list:
    # list가 아니면 빈 list로 치환
    return x if isinstance(x, list) else []


def pick(*vals: Any) -> Any:
    # 여러 후보 값 중 비어있지 않은 첫 번째 값을 선택
    for v in vals:
        if v is None:
            continue
        if isinstance(v, str) and v.strip() == "":
            continue
        if isinstance(v, (list, dict)) and len(v) == 0:
            continue
        return v
    return None


def to_standard_record(row: Dict[str, Any], detail: Dict[str, Any]) -> Dict[str, Any]:
    # 목록 + 상세 데이터를 표준 CSV 레코드 형태로 변환
    detail = safe_dict(detail)
    org = safe_dict(detail.get("pbancOrgMap"))
    bid = safe_dict(detail.get("bidPbancMap"))

    # 수집 시각 기록용
    now = datetime.now().isoformat(timespec="seconds")
    bid_id = build_bid_id(row)

    # 기본 입찰 정보 매핑
    rec = {
        BID_FULL_NO_COLUMN: pick(bid.get("bidPbancFullNo"), org.get("bidPbancFullNo"), row.get("bidPbancFullNo")),
        "문서번호": pick(bid.get("usrDocNoVal"), org.get("usrDocNoVal")),
        "긴급입찰여부": pick(bid.get("emrgPbancYnLtrs"), org.get("emrgPbancYnLtrs")),
        "공고종류": pick(bid.get("pbancKndCdNm"), org.get("pbancKndCdNm")),
        "공고처리구분": pick(bid.get("pbancSttsCdNm"), org.get("pbancSttsCdNm")),
        "업무분류": pick(bid.get("prcmBsneSeCdNm"), org.get("prcmBsneSeCdNm")),
        "입찰공고명": pick(bid.get("bidPbancNm"), org.get("bidPbancNm"), row.get("bidPbancNm")),
        "입찰방식": pick(bid.get("bidMthdCdNm"), org.get("bidMthdCdNm")),
        "계약방법": pick(bid.get("stdCtrtMthdCdNm"), org.get("stdCtrtMthdCdNm")),
        "낙찰방법": pick(bid.get("scsbdMthdCdNm"), org.get("scsbdMthdCdNm")),
        "재입찰여부": pick(bid.get("rbidPrmsYnLtrs"), org.get("rbidPrmsYnLtrs")),

        # 입찰 주요 일정 정보
        "입찰서접수시작일시": pick(
            bid.get("slprRcptBgngDtIndt"), bid.get("slprRcptBgngDt"),
            org.get("slprRcptBgngDtIndt"), org.get("slprRcptBgngDt")
        ),
        "입찰서접수마감일시": pick(
            bid.get("slprRcptDdlnDt"), bid.get("slprRcptDdlnDt"),
            org.get("slprRcptDdlnDtIndt"), org.get("slprRcptDdlnDt")
        ),
        "등록마감일시": pick(
            bid.get("bidQlfcRegDtIndt"), bid.get("bidQlfcRegDt"),
            org.get("bidQlfcRegDtIndt"), org.get("bidQlfcRegDt")
        ),
        "개찰일시": pick(
            bid.get("onbsPrnmntDtIndt"), bid.get("onbsPrnmntDt"),
            org.get("onbsPrnmntDtIndt"), org.get("onbsPrnmntDt")
        ),
        "개찰장소": pick(bid.get("onbsPlacNm"), org.get("onbsPlacNm")),

        # 담당자 정보
        "담당부서": org.get("ogdpDeptNm"),
        "담당자": pick(org.get("picIdNm"), org.get("pbancPicNm"), org.get("bidBlffIdNm")),
        "담당자전화": (
            "'" + str(pick(
                org.get("picIdBaseTlphNo"),
                org.get("mngOfceTlphNo"),
                org.get("bsneTlphNo")
            ))
        ),
        "담당자이메일": org.get("bsneEml"),

        # 금액 및 제한 조건
        "부가가치세포함여부": pick(bid.get("vatAplcnYnLtrs"), org.get("vatAplcnYnLtrs")),
        "배정예산": pick(bid.get("alotBgtAmt"), org.get("alotBgtAmt")),
        "기준금액사용여부": pick(bid.get("pnprUseYn"), org.get("pnprUseYn")),
        "기준금액공개여부": pick(bid.get("pnprRlsYn"), org.get("pnprRlsYn")),
        "기준금액": pick(bid.get("evlcrtAmt"), org.get("evlcrtAmt")),
        "지역제한": pick(bid.get("rgnLmtYnLtrs"), org.get("rgnLmtYnLtrs")),
        "지사/지점허용여부": pick(bid.get("bofcBdngPrmsYnLtrs"), org.get("bofcBdngPrmsYnLtrs")),
        "업종제한(표시)": pick(bid.get("lcnsLmtYnLtrs"), org.get("lcnsLmtYnLtrs")),

        # 용역 관련 필드 초기값
        "용역명": None,
        "완수기한": None,
        "용역현장명": None,
        "용역건수": 0,
    }

    # 용역(아이템) 목록 추출
    item_list = safe_list(detail.get("bidPbancItemlist"))

    # 용역 기본값 초기화
    rec["용역건수"] = 0
    rec["용역명"] = None
    rec["완수기한"] = None
    rec["용역현장명"] = None

    # 용역 정보가 있으면 첫 번째 항목 기준으로 매핑
    if item_list:
        rec["용역건수"] = len(item_list)

        item = safe_dict(item_list[0])

        rec["용역명"] = unescape_html(item.get("ibxSrvNm"))
        rec["완수기한"] = item.get("calFlmtTermYmdLtrs") or item.get("calFlmtTermYmd")
        rec["용역현장명"] = item.get("ibxSrstNm")

    # 표준화된 레코드 반환
    return rec
