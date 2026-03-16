# 채산 재료비율 분석 대시보드 v2

## v2 주요 수정사항

### 1. 재료비율 계산 수정 (핵심)
- **기존 문제**: `총자재비`(단위당 원가)를 그대로 합산 → 재료비율 ~1.3% (오류)
- **수정**: `총재료비 = 총자재비(단위당) × 입고수량` → 재료비율 ~67% (정상)

### 2. BOM 자재 매칭 수정
- **기존 문제**: BOM `material_id` = `자재코드`만 사용 → purchase(`자재코드+색상`)와 매칭 0건
- **수정**: BOM `material_id` = `자재코드 + 자재색상` → purchase와 직접 매칭 740건

### 3. 기타 개선
- DB 스키마에 `bom_monthly.material_code`, `material_color` 컬럼 추가
- `material_cost` 테이블에 `factory_price` 컬럼 추가
- 안분 로직 제거 (BOM-purchase가 동일 키이므로 불필요)

## 페이지 구성

| 페이지 | 설명 |
|--------|------|
| Upload | CSV 업로드 & Supabase 적재 |
| Overview | 월별 KPI (매출, 총재료비, 재료비율) |
| Contribution | 전월 대비 재료비율 기여도 TOP 품목 |
| Product Drilldown | 품목별 상세 분석 & BOM 자재 내역 |
| Material Analysis | 구매/BOM/재고 기반 자재 GAP 분석 |
| JIT Analysis | JIT 자재 초과구매 탐지 |

## 데이터 파일 형식

파일명: `YYYY-MM_dataset.csv`

| dataset | 필수 컬럼 |
|---------|-----------|
| receipt_performance | 단품코드, 단품명, 입고수량, 입고금액 |
| material_cost | 코드, 단품명칭, 총자재비 |
| bom | 단품코드, 자재코드, 자재명칭, 소요량 |
| purchase | 자재코드, 자재명, 입고량, 입고금액 |
| inventory_begin | 자재코드, 자재명, 현재고, 현재고금액 |
| inventory_end | 자재코드, 자재명, 현재고, 현재고금액 |
| jit_materials | 자재코드, 색상, 자재명 |

## 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Supabase 설정

`.streamlit/secrets.toml` 또는 환경변수에 설정:
```
SUPABASE_URL = "https://xxx.supabase.co"
SUPABASE_KEY = "eyJhbGciOi..."
```

DB 스키마는 `schema.sql`을 Supabase SQL Editor에서 실행하세요.
