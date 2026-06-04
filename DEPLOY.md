# 배포 가이드 (CI/CD)

이 저장소는 GitHub Actions로 **검증(테스트) → 자동 배포** 파이프라인이 구성되어 있습니다.

## 파이프라인 개요

| 워크플로 | 트리거 | 하는 일 |
| --- | --- | --- |
| `.github/workflows/ci.yml` | 모든 push / PR | Python 3.9–3.12에서 `pytest` 실행 |
| `.github/workflows/release.yml` | `v*` 태그 push | **테스트 통과 후** 3개 타깃으로 배포 |

`release.yml`의 잡 구조:

```
test (검증 게이트)
  └─ build (wheel + sdist)
        ├─ github-release  → GitHub 릴리스에 아티팩트 첨부
        └─ pypi            → PyPI 게시
  └─ docker               → GHCR에 이미지 push
```

세 배포 잡은 서로 독립적이라, 한 곳(예: PyPI)이 실패해도 나머지 배포는 계속됩니다.

## 릴리스(배포) 하는 법

```bash
# 1) 버전 올리기: pyproject.toml 의 version 수정 (예: 0.1.0 -> 0.2.0)
# 2) 커밋
git commit -am "Release v0.2.0"

# 3) 태그를 만들고 push  → 여기서 배포가 자동으로 시작됩니다
git tag v0.2.0
git push origin v0.2.0
```

> 태그의 버전(`v0.2.0`)과 `pyproject.toml`의 `version`을 일치시키세요.

## 타깃별 사전 설정

### 1. GitHub Release — 추가 설정 없음
빌드된 `*.whl` / `*.tar.gz`가 릴리스에 자동 첨부됩니다. 내장
`GITHUB_TOKEN`만 사용합니다.

### 2. Docker 이미지 (GHCR) — 추가 설정 없음
`ghcr.io/noainred/webcrawing` 로 이미지가 push 됩니다(`GITHUB_TOKEN` 사용).

```bash
# 사용 예시
docker pull ghcr.io/noainred/webcrawing:latest
docker run --rm ghcr.io/noainred/webcrawing https://example.com -d 2

# 결과 파일을 호스트로 받기 (현재 폴더를 마운트)
docker run --rm -v "$PWD:/out" ghcr.io/noainred/webcrawing \
  https://example.com -o /out/result.json
```

> 첫 배포 후 패키지는 기본 **private** 입니다. 공개하려면
> GitHub → 저장소/프로필의 **Packages → 해당 패키지 → Package settings →
> Change visibility → Public** 으로 바꾸세요.

### 3. PyPI — 1회 설정 필요
배포판 이름은 `pyproject.toml`의 `name = "webcrawling"` 입니다
(`webcrawler`는 PyPI에 이미 선점됨). 원하는 다른 이름으로 바꿔도 됩니다.

권장: **Trusted Publishing (OIDC)** — 토큰/시크릿 불필요, 더 안전합니다.

1. https://pypi.org 가입 후 로그인
2. **Account → Publishing → Add a new pending publisher** 에서 등록:
   - PyPI Project Name: `webcrawling` (pyproject의 name과 동일)
   - Owner: `noainred`
   - Repository name: `webcrawing`
   - Workflow name: `release.yml`
   - Environment name: `pypi`
3. GitHub 저장소 → **Settings → Environments → New environment → `pypi`** 생성
4. 끝. 이후 `v*` 태그를 push하면 자동 게시됩니다.

설치:
```bash
pip install webcrawling
webcrawler https://example.com
```

#### 대안: API 토큰 방식
Trusted Publishing 대신 토큰을 쓰려면:
1. PyPI → **Account → API tokens** 에서 토큰 생성
2. GitHub → **Settings → Secrets and variables → Actions** 에 `PYPI_API_TOKEN` 추가
3. `release.yml`의 `pypi` 잡에서 `environment`/`id-token` 줄을 지우고,
   `pypa/gh-action-pypi-publish` 단계에 다음을 추가:
   ```yaml
   with:
     password: ${{ secrets.PYPI_API_TOKEN }}
   ```

## 로컬에서 미리 확인하기

```bash
pytest -q                 # 검증
python -m build           # 배포 아티팩트 빌드 (pip install build 필요)
docker build -t webcrawling:dev .   # 이미지 빌드 확인
```
