import streamlit as st

st.set_page_config(
    page_title="채산 재료비율 분석 v2",
    page_icon="📊",
    layout="wide",
)

st.title("📊 채산 재료비율 분석 대시보드 v2")
st.caption("월별 재료비율 변화, 전월 대비 기여도, TOP 품목, 자재 원인 분석")

st.markdown(
    '''
### 시작 순서
1. **Upload** — CSV 형식 검증 및 Supabase 적재
2. **Overview** — 월별 KPI (매출, 총재료비, 재료비율)
3. **Contribution** — 전월 대비 상승 / 하락 TOP 품목
4. **Product Drilldown** — 품목별 원인 분석
5. **Material Analysis** — BOM / 구매 / 재고 GAP 분석
6. **JIT Analysis** — JIT 자재 초과구매 탐지
'''
)

st.divider()

st.info(
    "**v2 핵심 수정사항**\n\n"
    "- 총재료비 = 단위당 총자재비 × 입고수량 (기존: 단가 그대로 합산 → 재료비율 오류)\n"
    "- BOM 자재ID = 자재코드 + 자재색상 (기존: 자재코드만 → 구매/재고와 매칭 0건)\n"
    "- 매출 = 입고금액, 수량 = 입고수량 기준"
)
