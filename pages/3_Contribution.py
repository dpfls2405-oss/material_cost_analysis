from __future__ import annotations

import streamlit as st

from data_loader import load_standardized_data
from calculators import (
    build_product_base,
    calculate_monthly_totals,
    enrich_product_base,
    get_top_contributors,
    prepare_waterfall_frame,
)
from charts import bar_contribution, waterfall_contribution

st.title("🏆 Contribution")

data = load_standardized_data()
base = build_product_base(data.get("receipt_performance"), data.get("material_cost"))
monthly = calculate_monthly_totals(base)
enriched = enrich_product_base(base, monthly)

if enriched.empty or len(monthly) < 2:
    st.warning("전월 비교를 위해 최소 2개월 데이터가 필요합니다.")
    st.stop()

month_list = monthly["month"].tolist()[1:]
selected_month = st.selectbox("기준월", month_list, index=len(month_list) - 1)
top_n = st.slider("TOP 품목 수", min_value=5, max_value=30, value=20)

top_up = get_top_contributors(enriched, selected_month, top_n=top_n, ascending=False)
top_down = get_top_contributors(enriched, selected_month, top_n=top_n, ascending=True)

col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(bar_contribution(top_up, "재료비율 상승 TOP"), use_container_width=True)
with col2:
    st.plotly_chart(bar_contribution(top_down, "재료비율 하락 TOP"), use_container_width=True)

cur_ratio = monthly.loc[monthly["month"] == selected_month, "material_ratio"].iloc[0]
prev_ratio = monthly.loc[monthly["month"] == selected_month, "prev_material_ratio"].iloc[0]
wf = prepare_waterfall_frame(enriched, selected_month, top_n=10)
st.plotly_chart(waterfall_contribution(prev_ratio, wf, cur_ratio), use_container_width=True)

st.subheader("상승 TOP 품목 상세")
st.dataframe(top_up, use_container_width=True)

st.subheader("하락 TOP 품목 상세")
st.dataframe(top_down, use_container_width=True)
