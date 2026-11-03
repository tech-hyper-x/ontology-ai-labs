# 원천 데이터 출처 (data/raw)

제조 실습의 원천 데이터는 NASA JPL Open Source Rover 공개 저장소다. 내려받은 파일은 용량과 라이선스 표기를 위해 **git 에 커밋하지 않고**, 이 문서의 명령으로 누구나 같은 스냅샷을 다시 받을 수 있게 한다 (개발환경 정의서 5.1 — 원천 · 정규화 · 적재 · 평가 데이터 구분, 출처와 버전 기록).

## 1. NASA JPL Open Source Rover 저장소

| 항목 | 값 |
|---|---|
| 출처 | https://github.com/nasa-jpl/open-source-rover |
| 라이선스 | Apache-2.0 (`LICENSE.txt`) |
| 스냅샷 커밋 | `a78f9eb33e8163204e81c86140f751ce04e6538b` (2026-10-22) |
| 받은 날 | 2026-10-25 |
| 위치 | `data/raw/nasa-osr/` |
| 크기 | 약 15MB (전체 저장소는 이력 포함 약 3GB — 이미지 · CAD · PCB 설계 파일 제외) |

전체 커밋 이력(1,019개)은 남기고, 파일 내용은 실습에 필요한 경로만 받았다 (partial clone + sparse checkout).

```bash
git clone --filter=blob:none --no-checkout https://github.com/nasa-jpl/open-source-rover.git data/raw/nasa-osr
```

```bash
cd data/raw/nasa-osr && git sparse-checkout init --no-cone && git sparse-checkout set '/parts_list/' '/electrical/pcb/control_board/BOM/' '/expansion/' '*.md' '/LICENSE*' && git checkout a78f9eb33e8163204e81c86140f751ce04e6538b
```

### 실습에서 쓰는 파일

| 파일 | 내용 | 실습 초안의 기대값 | 실제 |
|---|---|---|---|
| `parts_list/parts_list.csv` | 기계 BOM. 열: assembly, short name, part #, long name, link, cost pp, # req in assy, assembly multiplier | 부품 60종, 어셈블리 5개, 약 $1,330 | 60행, 5개 (drive wheel ×6, corner ×4, rocker bogie ×2, body, general), **$1,330.38** (단가 × 어셈블리당 수량 × 배수) |
| `parts_list/digikey_bom.csv` | 전장 부품 Digi-Key 주문서 | 33라인, 약 $91 | 34라인, $90.80 |
| `electrical/pcb/control_board/BOM/bom_v2.0.3_*.csv` | 제어 보드 BOM (회로 위치 · 제조사 품번 · Digi-Key 번호) | 약 50종 | board_ref 38행 + other 14행 |
| `parts_list/parts_list.csv` 의 git 이력 | 교육용 ECN 의 원재료 | 커밋 24건 | **24건** (2023-05 ~ 2026-08) |
| `mechanical/servo_gear_replacement/README.md` 등 `*.md` | 정비 · 조립 문서 (벡터 검색 대상) | 정비 가이드 · 조립 README | 저장소의 모든 README 포함 |
| `expansion/mast/` | 옵션 모듈 (확장 과제) | 마스트 옵션 BOM | README · STL · 사진 |

실습 초안이 짚은 데이터 특징도 그대로 들어 있다: 수량 0.5 (2-pack 을 반으로 쓰는 부품 3종), 이름에 "2pack" 이 들어간 포장 단위 부품, `general` 어셈블리의 배수가 1 과 2 로 섞임.

교육용 ECN 후보가 되는 parts_list.csv 커밋 예:

| 날짜 | 커밋 | 내용 |
|---|---|---|
| 2023-10-04 | `b6b321f` | 41-hole beam 6개 → 4개 |
| 2023-10-06 | `2d9912e` | standoff 20mm → 22mm |
| 2023-11-18 | `e7eb957` | 알루미늄 중공축 → 같은 치수 스테인리스 축 |
| 2024-06-18 | `e7a5cd9` | 더 작은 Wasteland 휠로 교체 |
| 2026-08-05 | `6b2c5a9` | hurricane nut → goRail nut |

## 2. GitHub 이슈 (현장 이슈 · 증상 문서)

| 항목 | 값 |
|---|---|
| 출처 | https://github.com/nasa-jpl/open-source-rover/issues (GitHub REST API) |
| 받은 날 | 2026-10-25 |
| 위치 | `data/raw/nasa-osr-github/issues.json` |
| 내용 | 이슈 288건 + PR 237건의 제목 · 본문 · 라벨 · 상태 · 날짜 · URL (2018-06 ~ 2026-09) |
| 빠진 것 | 댓글 스레드 (인증 없이는 API 호출 한도가 시간당 60회라 받지 않았다) |

다시 받기: `https://api.github.com/repos/nasa-jpl/open-source-rover/issues?state=all&per_page=100&page=N` 을 빈 결과가 나올 때까지 받아 합친다.

## 주의

- 내려받은 저장소 안의 스크립트(`parts_list/csv_to_md.py`, `*.sh` 등)는 실행하지 않는다. 데이터로만 쓴다.
- 단가는 2026-10-22 스냅샷 시점의 공개 가격이다. 교육용 가격 이력 · 가상 공급사는 이 값을 바탕으로 따로 만들고, "교육용"으로 표시한다 (정의서 5.2).
