# webcrawler

HTML 기반의 가볍고 예의 바른(polite) 웹 크롤러입니다. 시작 URL에서 출발해
링크를 너비 우선(BFS)으로 따라가며, 각 페이지를 BeautifulSoup으로 파싱해
**제목 · 메타 설명 · 본문 텍스트 · 링크**를 추출합니다.

기본적으로 다음을 지킵니다.

- **같은 도메인 안에서만** 크롤링 (외부 링크는 따라가지 않음)
- **`robots.txt` 준수** (`Crawl-delay` 포함)
- **호스트별 요청 간격(politeness delay)** 으로 서버에 부담을 주지 않음
- 일시적 오류(429·5xx)에 대한 **재시도 + 지수 백오프**
- HTML이 아닌 리소스(이미지·PDF 등)는 **본문을 내려받지 않고** 헤더만 기록

## 설치

```bash
# 의존성 설치
pip install -r requirements.txt

# (선택) 패키지로 설치하면 `webcrawler` 명령을 쓸 수 있습니다
pip install -e .
```

의존성: `requests`, `beautifulsoup4`, `lxml`
(테스트 실행 시 `pytest` 추가로 필요)

## 명령줄(CLI) 사용법

```bash
# 가장 단순한 사용: 한 사이트를 깊이 2까지 크롤링
python main.py https://example.com

# 깊이 3, 최대 100페이지, 결과를 JSON으로 저장, 진행 로그 출력
python main.py https://example.com -d 3 -n 100 -o result.json -v

# 특정 경로만 크롤링하고 일부는 제외 (정규식)
python main.py https://example.com --include "/blog/" --exclude "\.pdf$"

# 외부 도메인까지 따라가기 + 요청 간격 1초
python main.py https://example.com --allow-external --delay 1.0

# `pip install -e .` 후에는 콘솔 명령으로도 동일하게 실행
webcrawler https://example.com -o result.csv
```

### 주요 옵션

| 옵션 | 설명 | 기본값 |
| --- | --- | --- |
| `-d, --max-depth` | 시작 URL로부터 따라갈 링크 깊이 | `2` |
| `-n, --max-pages` | 가져올 최대 페이지 수 | `100` |
| `--delay` | 같은 호스트에 대한 최소 요청 간격(초) | `0.5` |
| `--allow-external` | 다른 도메인 링크도 따라감 | 꺼짐 |
| `--no-subdomains` | 서브도메인을 범위 밖으로 취급 | 꺼짐 |
| `--no-robots` | `robots.txt`를 무시 (책임 있게 사용) | 꺼짐 |
| `--include` / `--exclude` | URL 포함/제외 정규식 | 없음 |
| `-o, --output` | 결과 저장 파일 | 없음 |
| `-f, --format` | `json` · `jsonl` · `csv` | 확장자로 추론 |
| `-v` / `-vv` | 진행 / 디버그 로그 | 경고만 |

## 라이브러리로 사용하기

```python
from webcrawler import Crawler, CrawlConfig

config = CrawlConfig(max_depth=2, max_pages=50, delay=0.5)

with Crawler(config) as crawler:
    # 스트리밍: 페이지를 가져오는 즉시 처리
    for page in crawler.crawl("https://example.com"):
        print(page.status_code, page.url, page.title)

    # 또는 한 번에 전체 결과 받기
    # pages = crawler.run("https://example.com")
```

`Page` 객체에는 다음 정보가 담깁니다.

```python
page.url            # 최종 URL (리다이렉트 반영)
page.status_code    # HTTP 상태 코드
page.depth          # 시작점으로부터의 깊이
page.title          # <title> 또는 첫 <h1>
page.description    # meta description / og:description
page.text           # 스크립트·스타일을 제거한 본문 텍스트(길이 제한)
page.links          # 정규화된 절대 링크 목록
page.content_type   # 응답 Content-Type
page.error          # 실패 시 사유 (성공이면 None)
```

결과 저장:

```python
from webcrawler import storage
storage.save(crawler.pages, "result.json")   # 확장자로 형식 추론
storage.save(crawler.pages, "result.csv", fmt="csv")
```

## 구조

```
webcrawler/
├── models.py     # FetchResult, Page 데이터 구조
├── urls.py       # URL 정규화 · 스코프(같은 도메인) 판정
├── fetcher.py    # 타임아웃·재시도·크기 제한이 있는 HTTP 가져오기
├── parser.py     # BeautifulSoup 기반 제목/설명/본문/링크 추출
├── robots.py     # robots.txt 가져오기·캐시·허용 판정
├── crawler.py    # BFS 크롤 엔진 (스코프·예의·깊이/페이지 제한)
├── storage.py    # JSON / JSONL / CSV 저장
└── cli.py        # argparse 기반 명령줄 인터페이스
tests/            # pytest (로컬 픽스처 서버로 end-to-end 검증)
```

## 테스트

테스트는 실제 외부 네트워크 없이, 인메모리 HTTP 서버에 가짜 사이트를 띄워
크롤러를 처음부터 끝까지 검증합니다.

```bash
pip install pytest
pytest -q
```

## 책임 있는 크롤링 안내

- 기본적으로 `robots.txt`와 요청 간격을 지킵니다. 가능한 한 그대로 사용하세요.
- 크롤링 대상 사이트의 이용약관을 확인하고, 과도한 트래픽을 보내지 마세요.
- `--no-robots`, `--allow-external`, `--delay 0` 같은 옵션은 본인에게 권한이
  있는 사이트나 테스트 환경에서만 사용하세요.

## 라이선스

MIT
