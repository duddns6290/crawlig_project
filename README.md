# 누리장터 입찰공고 크롤러

누리장터 입찰공고 목록과 상세 API를 순회하며
주요 입찰 정보를 중복 없이, 중단 지점부터 이어서 수집하는 크롤러입니다.

입찰공고번호 기준 중복 저장 방지
실행 중단 후 재실행 시 자동 재개
단발 실행(once) 및 반복 실행(interval) 지원
CSV 저장 및 Excel(xlsx) 변환 지원

## 실행 방법

1. 쿠키 준비

1) https://nuri.g2b.go.kr 페이지로 이동
2) F12(개발자도구) → Network 탭
3) 입찰공고 > 입찰공고 목록 이동
4) selectBidPbancList.do 요청 선택
5) Request Headers의 Cookie 전체 복사

2. 단발 실행 (프로젝트 루트파일에서 실행(ex.CRAWLING_PROJECT))
python -m B_CRAWLING.main --cookie "JSESSIONID=...; WMONID=...;(쿠키 예시)"

"JSESSIONID=...; WMONID=...;(쿠키 예시)"부분에서 ""안에 복사한 쿠키를 넣으면 됩니다.


3. 반복 실행(interval)
python -m B_CRAWLING.main --cookie "..." --mode interval --interval-sec 3600 

## 출력 파일

result.csv

## 의존성 및 실행 환경

- Python 3.9 이상
- requests
- pandas
- openpyxl

의존성 설치 방법

pip install -r requirements.txt

별도의 외부 서비스 계정이나 DB 설정은 필요하지 않습니다.

## 설계 및 주요 가정

- 누리장터 입찰공고는 목록 API와 상세 API로 분리되어 제공된다는 것을 전제
- 입찰공고번호(Full)는 입찰공고를 식별할 수 있는 키라고 가정
- 동일 키워드로 반복 실행 시, 이전에 수집된 데이터는 재수집하지 않는 것을 기본 동작으로 함
- 세션 인증은 브라우저에서 획득한 Cookie를 그대로 사용하는 방식으로 처리
- API 응답 형식은 단기간 내 급격히 변경되지 않는다고 가정

## 한계 및 개선 아이디어

- Cookie 기반 인증 방식으로 인해 세션 만료 시 재실행이 필요
- 대량 수집 환경을 고려한 IP 분산, 프록시 처리는 미포함
- API 변경이나 필드 추가에 대한 자동 스키마 감지 기능은 없음

향후 개선

- 인증 갱신 자동화를 통한 무중단 수집 구조 개선
- 수집 결과를 DB(PostgreSQL 등)에 적재하도록 확장
- 필드 매핑을 설정 파일 기반으로 분리하여 유지보수성 향상


## 프로젝트 구조
CRAWLING_PROJECT
   -B_CRAWLING/
    ├── main.py              CLI 실행 진입점
    ├── config.py            URL, 대기시간, 출력 경로 설정
    ├── crawler.py           크롤링 흐름 제어
    ├── http_client.py       목록/상세 API 요청
    ├── mapper.py            표준 레코드 변환
    ├── checkpoints/
    │   └── crawl_state.json 키워드별 재개 페이지 저장
    └── result.csv           수집 결과
   -README.md
   -requirements.txt
   -result.csv
