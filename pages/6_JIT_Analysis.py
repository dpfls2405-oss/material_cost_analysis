from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from data_loader import load_standardized_data
from calculators import build_material_analysis
from helpers import fmt_krw

st.title("⚡ JIT Analysis")
st.caption("JIT 자재의 BOM 대비 실사용 차이 분석 — 분실·품질부적합 재구매 탐지")

data = load_standardized_data()
jit_master = data.get("jit_materials", pd.DataFrame())

if jit_master.empty:
    st.warning("JIT 자재 목록이 없습니다. Upload 페이지에서 업로드해 주세요.")
    st.stop()

analysis = build_material_analysis(
    data.get("purchase"),
    data.get("inventory_begin"),
    data.get("inventory_end"),
    data.get("bom"),
    data.get("receipt_performance"),
)

if analysis.empty:
    st.warning("분석에 필요한 구매/BOM/입고실적 데이터가 없습니다.")
    st.stop()

months = sorted(analysis["month"].dropna().unique().tolist())
if not months:
    st.warning("분석 가능한 월 데이터가 없습니다.")
    st.stop()

selected_month = st.selectbox("기준월", months, index=len(months) - 1)

jit_months = sorted(jit_master["month"].dropna().unique().tolist())
jit_month = selected_month if selected_month in jit_months else (jit_months[-1] if jit_months else None)

if jit_month is None:
    st.warning("JIT 자재 목록 데이터가 없습니다.")
    st.stop()

if jit_month != selected_month:
    st.info(f"선택월({selected_month}) JIT 목록 없음 → 최근 목록({jit_month}) 사용")

jit_ids = set(jit_master[jit_master["month"] == jit_month]["material_id"].dropna().unique())
month_analysis = analysis[analysis["month"] == selected_month].copy()
jit_analysis = month_analysis[month_analysis["material_id"].isin(jit_ids)].copy()

# ── KPI ──
st.divider()
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("JIT 자재 수", f"{len(jit_ids):,}개")
c2.metric("분석 가능", f"{len(jit_analysis):,}개")
c3.metric("수량 GAP 계산 가능", f"{jit_analysis['usage_gap_qty'].notna().sum():,}개")
total_gap = jit_analysis["usage_gap_amount"].fillna(0).sum()
c4.metric("금액차이 합계", fmt_krw(total_gap), delta=fmt_krw(total_gap), delta_color="inverse")
over = (jit_analysis["usage_gap_amount"].fillna(0) > 0).sum()
c5.metric("초과 구매 자재", f"{over:,}개")

st.divider()

tab1, tab2, tab3 = st.tabs(["💰 금액 초과 TOP", "📦 수량 GAP TOP", "📋 전체 JIT 자재 현황"])

with tab1:
    st.subheader("구매금액 - BOM 예상소요금액 초과 TOP 30")
    amt_df = jit_analysis[jit_analysis["usage_gap_amount"].notna()].sort_values("usage_gap_amount", ascending=False)
    if amt_df.empty:
        st.info("금액 GAP 데이터가 없습니다.")
    else:
        top30 = amt_df.head(30).sort_values("usage_gap_amount", ascending=True)
        colors = ["#e74c3c" if v > 0 else "#2ecc71" for v in top30["usage_gap_amount"]]
        fig = go.Figure(go.Bar(
            x=top30["usage_gap_amount"],
            y=top30["material_name"].fillna(top30["material_id"]),
            orientation="h", marker_color=colors,
            customdata=top30[["material_id", "purchase_amount", "expected_usage_amount"]].values,
            hovertemplate="<b>%{y}</b><br>자재ID: %{customdata[0]}<br>"
                          "구매금액: %{customdata[1]:,.0f}<br>BOM예상: %{customdata[2]:,.0f}<br>"
                          "차이: %{x:,.0f}<extra></extra>",
        ))
        fig.update_layout(
            title="JIT 자재 금액 GAP TOP 30",
            xaxis=dict(title="구매금액 - BOM예상금액", tickformat=","),
            height=700,
        )
        st.plotly_chart(fig, use_container_width=True)

        show_cols = ["material_id", "material_name", "purchase_qty", "purchase_amount",
                     "expected_usage_qty", "expected_usage_amount", "usage_gap_amount"]
        existing = [c for c in show_cols if c in amt_df.columns]
        st.dataframe(amt_df[existing].head(50), use_container_width=True)

with tab2:
    st.subheader("실사용량 - BOM 예상소요량 GAP TOP 30")
    qty_df = jit_analysis[jit_analysis["usage_gap_qty"].notna()].sort_values("usage_gap_qty", ascending=False)
    if qty_df.empty:
        st.info("수량 GAP 데이터가 없습니다.")
    else:
        top30q = qty_df.head(30).sort_values("usage_gap_qty", ascending=True)
        colors_q = ["#e74c3c" if v > 0 else "#2ecc71" for v in top30q["usage_gap_qty"]]
        fig2 = go.Figure(go.Bar(
            x=top30q["usage_gap_qty"],
            y=top30q["material_name"].fillna(top30q["material_id"]),
            orientation="h", marker_color=colors_q,
            customdata=top30q[["material_id", "actual_usage_qty", "expected_usage_qty"]].values,
            hovertemplate="<b>%{y}</b><br>자재ID: %{customdata[0]}<br>"
                          "실사용량: %{customdata[1]:,.1f}<br>BOM예상: %{customdata[2]:,.1f}<br>"
                          "차이: %{x:,.1f}<extra></extra>",
        ))
        fig2.update_layout(
            title="JIT 자재 수량 GAP TOP 30",
            xaxis=dict(title="실사용량 - BOM예상량", tickformat=","),
            height=700,
        )
        st.plotly_chart(fig2, use_container_width=True)

        show_q = ["material_id", "material_name", "begin_qty", "purchase_qty",
                   "actual_usage_qty", "expected_usage_qty", "usage_gap_qty"]
        existing_q = [c for c in show_q if c in qty_df.columns]
        st.dataframe(qty_df[existing_q].head(50), use_container_width=True)

with tab3:
    st.subheader("전체 JIT 자재 현황")
    jit_detail = jit_master[jit_master["month"] == jit_month].copy()

    col_a, col_b = st.columns(2)
    with col_a:
        if "vendor_name" in jit_detail.columns:
            vc = (
                jit_detail.groupby("vendor_name", dropna=False)["material_id"]
                .count().reset_index()
                .rename(columns={"vendor_name": "거래처명", "material_id": "JIT자재수"})
                .sort_values("JIT자재수", ascending=False).head(15)
            )
            fig3 = px.bar(
                vc.sort_values("JIT자재수"), x="JIT자재수", y="거래처명",
                orientation="h", title="거래처별 JIT 자재 수",
                color_discrete_sequence=["#3498db"],
            )
            st.plotly_chart(fig3, use_container_width=True)
    with col_b:
        matched = len(jit_analysis)
        unmatched = len(jit_ids) - matched
        fig4 = px.pie(
            values=[matched, unmatched],
            names=["분석 매칭됨", "구매/BOM 데이터 없음"],
            title="JIT 자재 분석 매칭 현황",
            color_discrete_sequence=["#2ecc71", "#bdc3c7"],
        )
        st.plotly_chart(fig4, use_container_width=True)

    st.subheader(f"JIT 자재 목록 ({jit_month} 기준, {len(jit_detail):,}개)")
    display_cols = ["material_id", "material_code", "material_color", "material_name",
                    "vendor_name", "unit_cost", "order_policy", "production_mgmt_no"]
    existing_d = [c for c in display_cols if c in jit_detail.columns]
    st.dataframe(jit_detail[existing_d], use_container_width=True)
