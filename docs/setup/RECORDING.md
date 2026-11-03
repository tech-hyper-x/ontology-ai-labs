# Ch3 설치 시연 체크리스트

설치 가이드: https://github.com/tech-hyper-x/ontology-ai-labs/blob/main/docs/setup/README.md

프롬프터의 비낭독 링크를 새 창으로 열어 진행합니다. 최초 다운로드·마이그레이션·API 대기 시간은 PC별로 달라, 원고의 핵심 시연 배분과 구분해 촬영합니다. 준비된 PC에서는 삭제·재설치 대신 기존 상태임을 알리고 절차를 설명할 수 있습니다.

|순서|보여줄 화면|확인할 결과|
|---|---|---|
|1|Docker 공식 다운로드 페이지 → 칩 종류|Mac에 맞는 설치 파일 선택|
|2|Docker.dmg → Applications → Docker 실행|엔진 실행 중|
|3|터미널 버전·hello-world|CLI와 실제 컨테이너 실행|
|4|GitHub Code 메뉴 → 프로젝트 폴더|labs/mfg-bom-agent와 Compose 파일|
|5|.env.example과 설정 항목|DB·Langfuse 로그인·LLM·임베딩 역할 구분|
|6|Compose 이미지 다운로드·상태|다운로드 완료, 서비스 목록|
|7|Neo4j 실행 → localhost:7474|연결 후 RETURN 1 성공|
|8|Langfuse 실행 → localhost:3000|초기 사용자 로그인과 제조 프로젝트|
|9|초기화·환경 점검 출력|적재·검사·문서 연결·색인|
|10|MCP·앱 → 질문 실행 → Langfuse|실제 도구 결과와 수집된 실행 기록|

실제 비밀번호·API 키 입력은 녹화하지 않습니다. Docker 설치 약관이나 로그인은 수강생 본인이 확인합니다. 초기화는 전용 실습 DB에서 진행하고, 이미 완료된 실행 결과를 새 설치 결과처럼 설명하지 않습니다.
