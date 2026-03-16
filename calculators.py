"""계산 엔진 v2.

핵심 수정:
1. 총재료비 = material_cost(단위당) × receipt_qty(입고수량)
2. BOM material_id가 자재코드+자재색상이므로 purchase와 직접 매칭 가능
"""
from __future__ import annotations

import pandas as pd
import numpy as np


# ─────────────────────────────────────────────────────────────
#  제품 베이스 (receipt × material_cost)
# ─────────────────────────────────────────────────────────────
def build_product_base(receipt_df, material_df) -> pd.DataFrame:
    """입고실적 + 재료비 병합 후 total_material_cost(총재료비) 계산.
    
    ★ 핵심: material_cost 테이블의 material_cost는 단위당 금액이므로
       total_material_cost = material_cost × receipt_qty
    """
    if receipt_df is None:
        receipt_df = pd.DataFrame()
    if material_df is None:
        material_df = pd.DataFrame()
    if receipt_df.empty and material_df.empty:
        return pd.DataFrame()

    base = receipt_df.merge(
        material_df,
        on=["month", "product_id"],
        how="outer",
        suffixes=("", "_mat"),
    )
    if "product_name_mat" in base.columns:
        base["product_name"] = base["product_name"].fillna(base["product_name_mat"])
        base.drop(columns=["product_name_mat"], inplace=True)

    base["sales_amount"] = base["sales_amount"].fillna(0.0)
    base["receipt_qty"] = base["receipt_qty"].fillna(0.0)
    base["material_cost"] = base["material_cost"].fillna(0.0)       # 단위당

    # ★ 총재료비 = 단위당 재료비 × 입고수량
    base["total_material_cost"] = base["material_cost"] * base["receipt_qty"]

    base = base.sort_values(["product_id", "month"]).reset_index(drop=True)
    return base


# ─────────────────────────────────────────────────────────────
#  월별 KPI
# ─────────────────────────────────────────────────────────────
def calculate_monthly_totals(base: pd.DataFrame) -> pd.DataFrame:
    if base is None or base.empty:
        return pd.DataFrame()

    monthly = base.groupby("month", as_index=False).agg(
        total_sales=("sales_amount", "sum"),
        total_material_cost=("total_material_cost", "sum"),   # ★ 총재료비 합계
        total_receipt_qty=("receipt_qty", "sum"),
        product_count=("product_id", "nunique"),
    )
    monthly["material_ratio"] = (
        monthly["total_material_cost"] / monthly["total_sales"].replace(0, np.nan)
    )
    monthly = monthly.sort_values("month").reset_index(drop=True)
    monthly["prev_material_ratio"] = monthly["material_ratio"].shift(1)
    monthly["material_ratio_change"] = monthly["material_ratio"] - monthly["prev_material_ratio"]
    return monthly


# ─────────────────────────────────────────────────────────────
#  품목별 기여도 분석
# ─────────────────────────────────────────────────────────────
def enrich_product_base(base: pd.DataFrame, monthly: pd.DataFrame) -> pd.DataFrame:
    if base is None or base.empty or monthly is None or monthly.empty:
        return pd.DataFrame()

    monthly_map = monthly[["month", "total_sales"]].copy()
    enriched = base.merge(monthly_map, on="month", how="left")

    # 품목별 재료비율 = 총재료비 / 매출금액
    enriched["product_material_ratio"] = (
        enriched["total_material_cost"] / enriched["sales_amount"].replace(0, np.nan)
    )
    enriched["sales_share"] = (
        enriched["sales_amount"] / enriched["total_sales"].replace(0, np.nan)
    )

    enriched = enriched.sort_values(["product_id", "month"]).reset_index(drop=True)
    grp = enriched.groupby("product_id", dropna=False)
    enriched["prev_sales_amount"] = grp["sales_amount"].shift(1)
    enriched["prev_total_material_cost"] = grp["total_material_cost"].shift(1)
    enriched["prev_receipt_qty"] = grp["receipt_qty"].shift(1)
    enriched["prev_product_material_ratio"] = grp["product_material_ratio"].shift(1)
    enriched["prev_sales_share"] = grp["sales_share"].shift(1)
    enriched["prev_month"] = grp["month"].shift(1)

    prev_total_map = monthly.rename(
        columns={"month": "prev_month", "total_sales": "prev_total_sales"}
    )[["prev_month", "prev_total_sales"]]
    enriched = enriched.merge(prev_total_map, on="prev_month", how="left")

    # 기여도 = (당월 총재료비/당월 총매출) - (전월 총재료비/전월 총매출)
    enriched["contribution"] = (
        enriched["total_material_cost"] / enriched["total_sales"].replace(0, np.nan)
        - enriched["prev_total_material_cost"] / enriched["prev_total_sales"].replace(0, np.nan)
    )
    enriched["mix_effect"] = (
        (enriched["sales_share"] - enriched["prev_sales_share"])
        * enriched["prev_product_material_ratio"]
    )
    enriched["rate_effect"] = (
        enriched["sales_share"]
        * (enriched["product_material_ratio"] - enriched["prev_product_material_ratio"])
    )
    return enriched


def get_top_contributors(enriched: pd.DataFrame, month: str, top_n: int = 20, ascending: bool = False) -> pd.DataFrame:
    current = enriched[enriched["month"] == month].copy()
    cols = [
        "product_id", "product_name",
        "sales_amount", "total_material_cost", "receipt_qty",
        "material_cost",                    # 단위당 재료비
        "product_material_ratio",
        "prev_product_material_ratio",
        "contribution", "mix_effect", "rate_effect",
    ]
    existing = [c for c in cols if c in current.columns]
    current = current[existing].fillna(0)
    return current.sort_values("contribution", ascending=ascending).head(top_n)


def prepare_waterfall_frame(enriched: pd.DataFrame, month: str, top_n: int = 10) -> pd.DataFrame:
    top = get_top_contributors(enriched, month, top_n=top_n, ascending=False).copy()
    return top[["product_name", "contribution"]]


# ─────────────────────────────────────────────────────────────
#  자재 사용량 분석 (구매 + 재고 → 실사용량)
# ─────────────────────────────────────────────────────────────
def build_material_usage(purchase_df, inventory_begin_df, inventory_end_df) -> pd.DataFrame:
    if purchase_df is None:
        purchase_df = pd.DataFrame()
    if inventory_begin_df is None:
        inventory_begin_df = pd.DataFrame()
    if inventory_end_df is None:
        inventory_end_df = pd.DataFrame()
    if purchase_df.empty and inventory_begin_df.empty and inventory_end_df.empty:
        return pd.DataFrame()

    begin = inventory_begin_df.copy()
    end = inventory_end_df.copy()

    purchase = purchase_df.groupby(["month", "material_id"], as_index=False).agg(
        material_name=("material_name", "first"),
        material_code=("material_code", "first") if "material_code" in purchase_df.columns else ("material_id", "first"),
        purchase_qty=("purchase_qty", "sum"),
        purchase_amount=("purchase_amount", "sum"),
    )

    frame = begin.merge(
        purchase, on=["month", "material_id"], how="outer", suffixes=("_begin", "")
    )
    if not end.empty:
        frame = frame.merge(
            end[["month", "material_id", "end_qty", "end_amount"]],
            on=["month", "material_id"], how="left",
        )
    else:
        frame["end_qty"] = np.nan
        frame["end_amount"] = np.nan

    # material_name 보완
    if "material_name_begin" in frame.columns:
        frame["material_name"] = frame["material_name_begin"].fillna(frame["material_name"])
    if "material_code_begin" in frame.columns:
        frame["material_code"] = frame["material_code_begin"].fillna(frame.get("material_code", np.nan))
    frame.drop(columns=[c for c in frame.columns if c.endswith("_begin")], errors="ignore", inplace=True)

    # 다음 월 기초재고를 기말재고 대체로 사용
    if not begin.empty:
        next_begin = begin[["month", "material_id", "begin_qty"]].copy()
        next_begin = next_begin.rename(columns={"month": "next_month", "begin_qty": "next_begin_qty"})
        months = sorted(begin["month"].dropna().astype(str).unique().tolist())
        month_next_map = {months[i]: months[i + 1] for i in range(len(months) - 1)}
        frame["next_month"] = frame["month"].map(month_next_map).astype(str).replace("nan", np.nan)
        next_begin["next_month"] = next_begin["next_month"].astype(str)
        frame = frame.merge(next_begin, on=["next_month", "material_id"], how="left")
        frame["calculated_end_qty"] = frame["end_qty"].fillna(frame.get("next_begin_qty", np.nan))
    else:
        frame["calculated_end_qty"] = frame["end_qty"]

    # 실사용량 = 기초재고 + 구매수량 - 기말재고
    frame["actual_usage_qty"] = (
        frame["begin_qty"].fillna(0) + frame["purchase_qty"].fillna(0) - frame["calculated_end_qty"]
    )
    frame.loc[frame["calculated_end_qty"].isna(), "actual_usage_qty"] = np.nan
    return frame


# ─────────────────────────────────────────────────────────────
#  BOM 기준 예상소요량
# ─────────────────────────────────────────────────────────────
def build_bom_expected_usage(bom_df, receipt_df) -> pd.DataFrame:
    """BOM × 입고수량 → 자재별 예상소요.
    
    v2: BOM의 material_id가 이미 자재코드+자재색상이므로
    purchase/inventory와 직접 매칭 가능.
    """
    if bom_df is None or (hasattr(bom_df, "empty") and bom_df.empty):
        return pd.DataFrame()
    if receipt_df is None or (hasattr(receipt_df, "empty") and receipt_df.empty):
        return pd.DataFrame()

    merged = bom_df.merge(
        receipt_df[["month", "product_id", "receipt_qty"]],
        on=["month", "product_id"],
        how="left",
    )
    merged["receipt_qty"] = merged["receipt_qty"].fillna(0)
    merged["expected_usage_qty"] = merged["unit_qty"].fillna(0) * merged["receipt_qty"]
    merged["expected_usage_amount"] = merged["bom_amount"].fillna(0) * merged["receipt_qty"]

    # material_id 기준 집계 (이미 자재코드+색상이므로 직접 사용)
    material_view = merged.groupby(["month", "material_id"], as_index=False).agg(
        material_name=("material_name", "first"),
        expected_usage_qty=("expected_usage_qty", "sum"),
        expected_usage_amount=("expected_usage_amount", "sum"),
    )
    return material_view


# ─────────────────────────────────────────────────────────────
#  통합 자재 분석 (usage vs expected)
# ─────────────────────────────────────────────────────────────
def build_material_analysis(purchase_df, inventory_begin_df, inventory_end_df, bom_df, receipt_df) -> pd.DataFrame:
    usage = build_material_usage(purchase_df, inventory_begin_df, inventory_end_df)
    expected = build_bom_expected_usage(bom_df, receipt_df)

    if usage.empty and expected.empty:
        return pd.DataFrame()

    # v2: BOM material_id == purchase material_id (둘 다 자재코드+색상)
    # 따라서 직접 outer join 가능 — 안분 로직 불필요
    if not usage.empty and not expected.empty:
        out = usage.merge(
            expected, on=["month", "material_id"], how="outer", suffixes=("", "_exp")
        )
        if "material_name_exp" in out.columns:
            out["material_name"] = out["material_name"].fillna(out["material_name_exp"])
            out.drop(columns=["material_name_exp"], inplace=True)
    elif not usage.empty:
        out = usage.copy()
        out["expected_usage_qty"] = np.nan
        out["expected_usage_amount"] = np.nan
    else:
        out = expected.copy()
        out["actual_usage_qty"] = np.nan
        out["purchase_amount"] = np.nan

    # GAP 계산
    out["usage_gap_qty"] = out.get("actual_usage_qty", np.nan) - out.get("expected_usage_qty", 0).fillna(0)
    out["usage_gap_amount"] = out.get("purchase_amount", pd.Series(0)).fillna(0) - out.get("expected_usage_amount", pd.Series(0)).fillna(0)
    out["usage_gap_qty_abs"] = out["usage_gap_qty"].abs()
    out["usage_gap_amount_abs"] = out["usage_gap_amount"].abs()

    return out


# ─────────────────────────────────────────────────────────────
#  품목별 BOM 자재 내역
# ─────────────────────────────────────────────────────────────
def get_product_material_breakdown(bom_df, product_id: str, month: str, receipt_qty: float) -> pd.DataFrame:
    if bom_df is None or (hasattr(bom_df, "empty") and bom_df.empty):
        return pd.DataFrame()
    product_bom = bom_df[(bom_df["product_id"] == product_id) & (bom_df["month"] == month)].copy()
    if product_bom.empty:
        return product_bom
    product_bom["expected_usage_qty"] = product_bom["unit_qty"] * receipt_qty
    product_bom["expected_usage_amount"] = product_bom["bom_amount"].fillna(0) * receipt_qty
    return product_bom.sort_values("expected_usage_amount", ascending=False)
