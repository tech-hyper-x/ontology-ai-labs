"""mfg_bom_agent — 제조 실습: NASA Open Source Rover BOM 변경 영향 분석 에이전트.

부품 변경(단가·공급사·대체품·Revision)이 어떤 조립품·제품에 영향을 주고 대당 원가가 얼마나 바뀌는지를
지식 그래프 탐색 + 계산 도구 + 문서 검색으로 답한다.

하위 패키지는 실습 흐름 순서대로 읽으면 된다 (개발환경_정의서 9절):

    config      설정
    contracts   도구 입력·출력과 답변의 Pydantic 계약
    graph       Neo4j 연결과 적재·조회
    retrieval   벡터 + 전문 + 그래프 Hybrid 검색
    tools       BOM 전개·구매 수량·원가 합산·영향 분석 계산 함수
    workflows   LangGraph 워크플로
    mcp_server  tools 를 MCP 도구로 노출
    ui          Streamlit 화면
"""
