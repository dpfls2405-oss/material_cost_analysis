from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def line_monthly_ratio(monthly: pd.DataFrame):
    fig = px.line(
        monthly, x="month", y="material_ratio",
        markers=True, title="월별 재료비율 추이",
    )
    fig.update_yaxes(tickformat=".1%")
    return fig


def bar_contribution(df: pd.DataFrame, title: str):
    fig = px.bar(
        df.sort_values("contribution", ascending=True),
        x="contribution", y="product_name",
        orientation="h", title=title,
        hover_data=["product_id", "sales_amount", "total_material_cost"],
    )
    fig.update_xaxes(tickformat=".2%")
    return fig


def waterfall_contribution(start_ratio: float, contrib_df: pd.DataFrame, end_ratio: float):
    x = ["전월 재료비율"] + contrib_df["product_name"].tolist() + ["당월 재료비율"]
    y = [start_ratio] + contrib_df["contribution"].tolist() + [end_ratio]
    measure = ["absolute"] + ["relative"] * len(contrib_df) + ["total"]
    fig = go.Figure(go.Waterfall(x=x, y=y, measure=measure))
    fig.update_layout(title="재료비율 Waterfall")
    fig.update_yaxes(tickformat=".2%")
    return fig


def line_product_metrics(product_df: pd.DataFrame):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=product_df["month"], y=product_df["sales_amount"],
        name="매출금액", mode="lines+markers",
        line=dict(color="#1f77b4", width=2), yaxis="y1",
    ))
    fig.add_trace(go.Scatter(
        x=product_df["month"], y=product_df["total_material_cost"],
        name="총재료비", mode="lines+markers",
        line=dict(color="#00bcd4", width=2), yaxis="y1",
    ))
    fig.add_trace(go.Scatter(
        x=product_df["month"], y=product_df["receipt_qty"],
        name="입고수량", mode="lines+markers",
        line=dict(color="#e74c3c", width=2, dash="dot"), yaxis="y2",
    ))
    fig.update_layout(
        title="품목 월별 추이",
        xaxis=dict(title="월"),
        yaxis=dict(title="금액 (원)", tickformat=",", side="left"),
        yaxis2=dict(title="수량 (개)", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
    return fig


def bar_material_gap(material_df: pd.DataFrame, title: str):
    chart_df = material_df[material_df["usage_gap_qty"].notna()].copy()
    chart_df = chart_df.reindex(
        chart_df["usage_gap_qty"].abs().sort_values(ascending=False).index
    ).head(20).sort_values("usage_gap_qty", ascending=True)
    fig = px.bar(
        chart_df, x="usage_gap_qty", y="material_name",
        orientation="h", title=title,
        color="usage_gap_qty",
        color_continuous_scale=["#2ecc71", "#f39c12", "#e74c3c"],
        hover_data=["material_id", "actual_usage_qty", "expected_usage_qty"],
    )
    fig.update_layout(coloraxis_showscale=False)
    return fig


def bar_material_gap_amount(material_df: pd.DataFrame, title: str):
    chart_df = material_df[material_df["usage_gap_amount"].notna()].copy()
    chart_df = chart_df.reindex(
        chart_df["usage_gap_amount"].abs().sort_values(ascending=False).index
    ).head(20).sort_values("usage_gap_amount", ascending=True)
    fig = px.bar(
        chart_df, x="usage_gap_amount", y="material_name",
        orientation="h", title=title,
        color="usage_gap_amount",
        color_continuous_scale=["#2ecc71", "#f39c12", "#e74c3c"],
        hover_data=["material_id", "purchase_amount", "expected_usage_amount"],
    )
    fig.update_xaxes(tickformat=",")
    fig.update_layout(coloraxis_showscale=False)
    return fig


def bar_bom_expected(material_df: pd.DataFrame, title: str):
    chart_df = material_df[
        material_df["expected_usage_qty"].notna() & (material_df["expected_usage_qty"] > 0)
    ].copy()
    chart_df = chart_df.sort_values("expected_usage_qty", ascending=True).tail(20)
    fig = px.bar(
        chart_df, x="expected_usage_qty", y="material_name",
        orientation="h", title=title,
        color_discrete_sequence=["#3498db"],
        hover_data=["material_id", "expected_usage_amount"],
    )
    fig.update_xaxes(tickformat=",")
    return fig
