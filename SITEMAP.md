# 가이드 바로 찾기

설치·실행·도구 사용 중 필요한 문서를 찾는 안내입니다. 현재 공개본은 **Ch3 공통 환경과 제조 실습 프로젝트**를 포함합니다.

## 처음 시작한다면

1. [Docker → Neo4j → Langfuse 상세 설치](docs/setup/README.md)
2. [Ch3 전체 실행 순서](docs/ch03-run-guide.md)
3. [그래프 사용처 조회 예제](examples/ch03_where_used.cypher)
4. [MCP 직접 호출·문서 검색 예제](examples/ch03_call.py)

## 하고 싶은 일로 찾기

|하고 싶은 일|열 문서|
|---|---|
|전체 구성과 다운로드 방법 확인|[README](README.md)|
|각 소프트웨어의 역할·준비 방법 확인|[설치 가이드 · 1절](docs/setup/README.md#1-무엇을-설치하나요)|
|Docker 설치와 실행 확인|[설치 가이드 · 2절](docs/setup/README.md#2-docker와-기본-도구-설치)|
|GitHub에서 코드를 내려받기|[설치 가이드 · 3절](docs/setup/README.md#3-github-프로젝트-다운로드)|
|.env·API 키·패키지 준비|[설치 가이드 · 4절](docs/setup/README.md#4-env와-python-패키지-준비)|
|서버 이미지 다운로드|[설치 가이드 · 5절](docs/setup/README.md#5-이미지-다운로드)|
|Neo4j 실행·로그인·첫 질의|[설치 가이드 · 6절](docs/setup/README.md#6-neo4j-설치실행-확인)|
|Langfuse 실행·로그인·프로젝트 확인|[설치 가이드 · 7절](docs/setup/README.md#7-langfuse-설치실행-확인)|
|데이터 적재와 검색 색인 준비|[설치 가이드 · 8절](docs/setup/README.md#8-실습-데이터와-검색-색인-준비)|
|MCP·앱 실행과 기록 확인|[설치 가이드 · 9절](docs/setup/README.md#9-mcp와-앱-실행)|
|종료하고 다음에 다시 실행|[설치 가이드 · 10절](docs/setup/README.md#10-종료와-다음-실행)|
|설치나 접속에서 막힘|[설치 가이드 · 11절](docs/setup/README.md#11-자주-막히는-곳)|
|설치 과정을 촬영·시연|[촬영 체크리스트](docs/setup/RECORDING.md)|

## 운영체제별 설치

OS별 도구 설치를 마치면 [공통 상세 설치 가이드](docs/setup/README.md)의 프로젝트 설정·초기화·첫 접속 순서를 따릅니다.

- [운영체제 선택](labs/mfg-bom-agent/INSTALL.md)
- [macOS](labs/mfg-bom-agent/docs/install/macos.md)
- [Windows · WSL2 Ubuntu](labs/mfg-bom-agent/docs/install/windows.md)
- [Linux · Ubuntu](labs/mfg-bom-agent/docs/install/linux.md)

## 도구별 사용법

|도구·주제|안내|
|---|---|
|Docker · Compose|[실행·로그·재시작·설정 반영·데이터 보존](labs/mfg-bom-agent/docs/DOCKER.md)|
|Neo4j Browser|[접속·Cypher 실행·그래프와 표 읽기](labs/mfg-bom-agent/docs/NEO4J_BROWSER.md)|
|Langfuse|[트레이스·도구 호출·실패 기록 확인](labs/mfg-bom-agent/docs/LANGFUSE.md)|
|임베딩 · Voyage|[계정·키 설정·색인·문제 해결](labs/mfg-bom-agent/docs/VOYAGE.md)|
|소프트웨어 구성|[역할·버전·라이선스·자원 사용량](labs/mfg-bom-agent/docs/SOFTWARE.md)|
|실습 화면|[화면 구성·실행 모드·근거 패널](labs/mfg-bom-agent/docs/UI_DESIGN.md)|

세부 도구 문서에는 이전 화면 기준 설명이 포함될 수 있습니다. Ch3의 초기 설치와 실행은 [공통 상세 설치 가이드](docs/setup/README.md)와 실제 코드 출력을 우선합니다.

## 제조 실습과 코드 위치

- [제조 프로젝트 개요](labs/mfg-bom-agent/README.md)
- [챕터별 실습 구간·오류 수정 과제](labs/mfg-bom-agent/HANDS_ON.md)
- [온톨로지 정의](labs/mfg-bom-agent/ontology/schema.yaml)
- [그래프 조회문](labs/mfg-bom-agent/queries/)
- [실행 스크립트](labs/mfg-bom-agent/scripts/)
- [Python 소스](labs/mfg-bom-agent/src/mfg_bom_agent/)
- [테스트](labs/mfg-bom-agent/tests/)
- [평가 결과와 해석](labs/mfg-bom-agent/docs/EVAL_RESULTS.md)

## 데이터 출처와 배포 정보

- [원천 자료·스냅샷·재수집 방법](labs/mfg-bom-agent/data/raw/SOURCES.md)
- [외부 자료 출처와 라이선스](THIRD_PARTY_NOTICES.md)
- [배포본의 원본 코드 커밋](DISTRIBUTION.json)

바이오 실습 프로젝트와 전체 커리큘럼의 단계별 GitLab 안내는 현재 공개 GitHub 배포본에 포함돼 있지 않습니다.

## Part 2 · Ch1 — 부품 변경 질문과 데이터 이해

[강의별 Hands-on 안내](docs/part02/ch01/README.md): 업무 질문·CQ 작성 → Neo4j 관찰 조회 → 원본과 가공 데이터 대조 → 출처·가정·시점 기록. 조회문 3개와 작성용 CSV 표를 제공합니다.
