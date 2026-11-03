"""원천 데이터 → 교육용 PLM · ERP · 품질 테이블 (Part 2 Ch1 · Ch2 · Ch3).

NASA JPL Open Source Rover 저장소(data/raw/nasa-osr)를 읽어 data/processed/ 의 CSV로 만든다.
흐름: sources(원천 읽기) → normalize(단위·식별자) → ecn(변경 이력) → virtual(교육용 가정) → build(저장).
"""
