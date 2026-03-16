from __future__ import annotations

import streamlit as st

from data_loader import load_standardized_data
from calculators import build_material_analysis
from charts import bar_material_gap, bar_material_gap_amount, bar_bom_expected
from helpers import fmt_krw

st.title("🧱 Material Analysis")

data = load_standardized_data()
analysis = build_material_analysis(
    data.get("purchase"),
    data.get("inventory_begin"),
    data.get("inventory_end"),
    data.get("bom"),
    data.get("receipt_performance"),
)

if analysis.empty:
    st.warning("자재 분석을 위한 데이터가 충분하지 않습니다.")
    st.stop()

months = sorted(analysis["month"].dropna().unique().tolist())
selected_month = st.selectbox("기준월", months, index=len(months) - 1)
month_df = analysis[analysis["month"] == selected_month].copy()

# ── KPI 요약 ──
col1, col2, col3, col4 = st.columns(4)
col1.metric("자재 수", f"{month_df['material_id'].nunique():,}")
col2.metric("구매금액 합계", fmt_krw(month_df["purchase_amount"].fillna(0).sum()))
col3.metric("BOM 예상소요금액", fmt_krw(month_df["expected_usage_amount"].fillna(0).sum()))
gap_total = month_df["usage_gap_amount"].fillna(0).sum()
col4.metric(
    "구매-예상 금액차이",
    fmt_krw(gap_total),
    delta=fmt_krw(gap_total),
    delta_color="inverse",
)

st.divider()

tab1, tab2, tab3 = st.tabs(["📦 수량 GAP 분석", "💰 금액 GAP 분석", "📋 BOM 예상 소요량"])

with tab1:
    st.subheader("실사용량 - BOM 예상소요량 (수량 기준)")
    st.caption("양수(+): 예상보다 더 사용 / 음수(-): 예상보다 덜 사용")

    qty_filter = st.radio(
        "표시 범위", ["전체", "초과만 (+)", "절감만 (-)"],
        horizontal=True, key="qty_filter",
    )
    qty_df = month_df.dropna(subset=["usage_gap_qty"]).copy()
    if qty_filter == "초과만 (+)":
        qty_df = qty_df[qty_df["usage_gap_qty"] > 0]
    elif qty_filter == "절감만 (-)":
        qty_df = qty_df[qty_df["usage_gap_qty"] < 0]

    st.info(f"수량 GAP 해당 자재: {len(qty_df):,}개")

    if len(qty_df) > 0:
        st.plotly_chart(bar_material_gap(qty_df, f"수량 GAP TOP 20 ({qty_filter})"), use_container_width=True)

    qty_cols = ["material_id", "material_name", "begin_qty", "purchase_qty",
                "calculated_end_qty", "actual_usage_qty", "expected_usage_qty", "usage_gap_qty"]
    existing = [c for c in qty_cols if c in qty_df.columns]
    display = qty_df[existing].copy()
    if "usage_gap_qty" in display.columns and not display.empty:
        display = display.iloc[display["usage_gap_qty"].abs().argsort()[::-1]]
    st.dataframe(display, use_container_width=True)

with tab2:
    st.subheader("구매금액 - BOM 예상소요금액 (금액 기준)")
    st.caption("양수(+): 예상보다 구매금액 초과 / 음수(-): 예상보다 구매금액 절감")

    amt_filter = st.radio(
        "표시 범위", ["전체", "초과만 (+)", "절감만 (-)"],
        horizontal=True, key="amt_filter",
    )
    amt_df = month_df.copy()
    if amt_filter == "초과만 (+)":
        amt_df = amt_df[amt_df["usage_gap_amount"].fillna(0) > 0]
    elif amt_filter == "절감만 (-)":
        amt_df = amt_df[amt_df["usage_gap_amount"].fillna(0) < 0]

    st.info(f"금액 GAP 해당 자재: {len(amt_df):,}개")

    if len(amt_df) > 0:
        st.plotly_chart(bar_material_gap_amount(amt_df, f"금액 GAP TOP 20 ({amt_filter})"), use_container_width=True)

    amt_cols = ["material_id", "material_name", "purchase_qty", "purchase_amount",
                "expected_usage_qty", "expected_usage_amount", "usage_gap_amount"]
    existing_a = [c for c in amt_cols if c in amt_df.columns]
    display_a = amt_df[existing_a].copy()
    if "usage_gap_amount" in display_a.columns and not display_a.empty:
        display_a = display_a.iloc[display_a["usage_gap_amount"].abs().argsort()[::-1]]
    st.dataframe(display_a, use_container_width=True)

with tab3:
    st.subheader("BOM 기준 예상 소요량")
    st.caption("입고실적 수량 × BOM 단위소요량으로 계산한 이론적 자재 소요량")

    bom_df = month_df[month_df["expected_usage_qty"].fillna(0) > 0].copy()
    if bom_df.empty:
        st.info("BOM 예상소요량 데이터가 없습니다.")
    else:
        st.plotly_chart(bar_bom_expected(bom_df, "BOM 예상소요량 TOP 20"), use_container_width=True)
        bom_cols = ["material_id", "material_name", "expected_usage_qty", "expected_usage_amount"]
        existing_b = [c for c in bom_cols if c in bom_df.columns]
        st.dataframe(
            bom_df[existing_b].sort_values("expected_usage_amount", ascending=False),
            use_container_width=True,
        )
