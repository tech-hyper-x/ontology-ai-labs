# 검색 준비 확인

- [ ] Ch4의 전용 실습 DB와 제공 Document가 준비됐다.
- [ ] 입력 원문·quality_document.csv·Document 청크의 역할을 구분했다.
- [ ] `build_index.py`로 문서 연결과 문서·질문 임베딩 및 색인을 준비했다.
- [ ] `doc_fulltext`와 `doc_vector`가 ONLINE이다.
- [ ] LabMeta에 공급자·모델·차원·대체 이유를 확인했다.
- [ ] Document와 SearchExample의 벡터 유무를 확인했다.
- [ ] `hash:local`은 실행 연결 점검으로만 기록했다. 의미 검색 비교는 의미 임베딩 준비 후 진행한다.
- [ ] Browser에서 저장된 질문을 선택했고, 질문 글자만 바꿔 기존 벡터를 재사용하지 않았다.

최초 임베딩 생성 시간과 API 사용료는 별도다. `build_index.py`는 문서 연결과 벡터 색인을 다시 구성한다. Ch4의 `load_graph.py`를 다시 실행하면 검색 준비가 초기화되므로 이 강의에서 반복하지 않는다.
