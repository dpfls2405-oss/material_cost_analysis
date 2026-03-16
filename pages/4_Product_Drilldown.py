from __future__ import annotations

import streamlit as st

from data_loader import load_standardized_data
from calculators import (
    build_product_base,
    calculate_monthly_totals,
    enrich_product_base,
    get_product_material_breakdown,
)
from charts import line_product_metrics
from helpers import fmt_krw, fmt_pct

st.title("🔎 Product Drilldown")

data = load_standardized_data()
base = build_product_base(data.get("receipt_performance"), data.get("material_cost"))
monthly = calculate_monthly_totals(base)
enriched = enrich_product_base(base, monthly)
bom = data.get("bom")

if enriched.empty:
    st.warning("표시할 데이터가 없습니다.")
    st.stop()

products = enriched[["product_id", "product_name"]].drop_duplicates().sort_values("product_name")
product_label_map = {f"{r.product_name} ({r.product_id})": r.product_id for r in products.itertuples()}

selected_label = st.selectbox("품목 선택", list(product_label_map.keys()))
selected_product = product_label_map[selected_label]

product_df = enriched[enriched["product_id"] == selected_product].copy().sort_values("month")
latest = product_df.iloc[-1]

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("매출", fmt_krw(latest["sales_amount"]))
col2.metric("단위당 재료비", fmt_krw(latest["material_cost"]))
col3.metric("총재료비", fmt_krw(latest["total_material_cost"]))
col4.metric("재료비율", fmt_pct(latest["product_material_ratio"]))
contrib = latest["contribution"]
col5.metric("기여도", fmt_pct(contrib) if contrib == contrib else "-")

st.plotly_chart(line_product_metrics(product_df), use_container_width=True)

st.subheader("월별 품목 지표")
display_cols = [
    "month", "sales_amount", "material_cost", "total_material_cost",
    "receipt_qty", "product_material_ratio", "prev_product_material_ratio",
    "contribution", "mix_effect", "rate_effect",
]
existing = [c for c in display_cols if c in product_df.columns]
st.dataframe(product_df[existing], use_container_width=True)

month_for_bom = st.selectbox("BOM 조회월", product_df["month"].tolist(), index=len(product_df) - 1)
receipt_qty = float(product_df.loc[product_df["month"] == month_for_bom, "receipt_qty"].iloc[0])
bom_breakdown = get_product_material_breakdown(bom, selected_product, month_for_bom, receipt_qty)

st.subheader("선택월 BOM 기준 예상 자재 소요")
if bom_breakdown.empty:
    st.info("해당 월 BOM 정보가 없습니다.")
else:
    st.dataframe(bom_breakdown, use_container_width=True)
