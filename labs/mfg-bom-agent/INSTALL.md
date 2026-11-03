# 설치 및 첫 실행 가이드 — mfg-bom-agent

Ch3의 Docker 설치 → Neo4j 접속 → Langfuse 로그인 순서는 [공개 상세 설치 가이드](../../docs/setup/README.md)에서 확인합니다. OS별 문서는 아래에서 선택합니다.

제조 실습 환경을 처음 설치하고 브라우저에서 확인하기까지의 과정을 운영체제별로 나눠 안내한다. **자기 운영체제 문서 하나만** 따라 하면 된다.

| 운영체제 | 문서 | 비고 |
|---|---|---|
| Windows 10/11 | [docs/install/windows.md](docs/install/windows.md) | WSL2(Ubuntu) 안에서 실행. Docker Desktop 사용 |
| macOS (Apple Silicon · Intel) | [docs/install/macos.md](docs/install/macos.md) | Homebrew 로 설치. Docker Desktop 또는 OrbStack |
| Linux (Ubuntu 22.04 / 24.04) | [docs/install/linux.md](docs/install/linux.md) | Docker Engine + Compose 플러그인 |

설치되는 소프트웨어의 목록·버전·용도·라이선스·자원 사용량은 [docs/SOFTWARE.md](docs/SOFTWARE.md) 에 정리되어 있다. 설치 후 Docker 사용법은 [docs/DOCKER.md](docs/DOCKER.md).

세 문서는 도구 설치(1단계)와 운영체제별 문제 해결만 다르고, 2~9단계(폴더 준비 → `.env` → 패키지 설치 → 컨테이너 → 초기화 → 실행 → 브라우저 확인 → 종료)는 같은 순서로 진행한다.

## 이 실습의 기본 포트

| 서비스 | 주소 |
|---|---|
| Streamlit 화면 | http://localhost:8501 |
| Neo4j Browser | http://localhost:7474 (Bolt 7687) |
| MCP 서버 | http://localhost:8000/mcp |
| Langfuse | http://localhost:3000 |

바이오 실습(bio-target-agent)과 기본 포트가 달라서 두 실습을 동시에 띄워도 충돌하지 않는다.
