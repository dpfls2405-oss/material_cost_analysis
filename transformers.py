"""CSV → 표준 DataFrame 변환기.

핵심 변경사항 (v2):
- material_cost.총자재비는 **단위당 원가**임을 명확히 하고,
  calculators에서 receipt_qty를 곱해 총재료비를 계산하도록 함
- BOM material_id = 자재코드 + 자재색상 (purchase/inventory와 동일한 키)
"""
from __future__ import annotations

import pandas as pd
from helpers import to_number, pct_to_float, normalize_text


# ── 입고실적 ─────────────────────────────────────────────────
def standardize_receipt(df: pd.DataFrame, month: str, source_file_name: str) -> pd.DataFrame:
    # Total/합계 행 제거
    df = df.copy()
    if "번호" in df.columns:
        df = df[~df["번호"].astype(str).str.strip().str.lower().isin(["total", "합계", "소계"])]
        df = df.reset_index(drop=True)

    if "색상" in df.columns:
        product_id = normalize_text(df["단품코드"]).fillna("") + normalize_text(df["색상"]).fillna("")
    else:
        product_id = normalize_text(df["단품코드"])

    # 빈 product_id 제거
    mask = product_id.str.strip() != ""
    df = df[mask].reset_index(drop=True)
    if "색상" in df.columns:
        product_id = normalize_text(df["단품코드"]).fillna("") + normalize_text(df["색상"]).fillna("")
    else:
        product_id = normalize_text(df["단품코드"])

    out = pd.DataFrame({
        "month": month,
        "product_id": product_id,
        "product_name": normalize_text(df["단품명"]),
        "receipt_qty": to_number(df["입고수량"]),
        "sales_amount": to_number(df["입고금액"]),
        "issue_qty": to_number(df["출고수량"]) if "출고수량" in df.columns else None,
        "issue_amount": to_number(df["출고금액"]) if "출고금액" in df.columns else None,
        "stock_qty": to_number(df["재고수량"]) if "재고수량" in df.columns else None,
        "brand": normalize_text(df["브랜드"]) if "브랜드" in df.columns else None,
        "product_category": normalize_text(df["제품구분"]) if "제품구분" in df.columns else None,
        "source_file_name": source_file_name,
    })
    return out.groupby(["month", "product_id"], as_index=False).agg({
        "product_name": "first",
        "receipt_qty": "sum",
        "sales_amount": "sum",
        "issue_qty": "sum",
        "issue_amount": "sum",
        "stock_qty": "sum",
        "brand": "first",
        "product_category": "first",
        "source_file_name": "first",
    })


# ── 재료비 (단위당 원가) ─────────────────────────────────────
def standardize_material_cost(df: pd.DataFrame, month: str, source_file_name: str) -> pd.DataFrame:
    if "색상" in df.columns:
        product_id = normalize_text(df["코드"]).fillna("") + normalize_text(df["색상"].astype(str)).fillna("")
    else:
        product_id = normalize_text(df["코드"])

    ratio_col = "제조원가율" if "제조원가율" in df.columns else None
    out = pd.DataFrame({
        "month": month,
        "product_id": product_id,
        "product_name": normalize_text(df["단품명칭"]),
        "material_cost": to_number(df["총자재비"]),              # 단위당 총자재비
        "factory_price": to_number(df["공장판매가"]) if "공장판매가" in df.columns else None,
        "manufacturing_cost": to_number(df["제조원가"]) if "제조원가" in df.columns else None,
        "manufacturing_ratio": pct_to_float(df[ratio_col]) if ratio_col else None,
        "series_name": normalize_text(df["시리즈"]) if "시리즈" in df.columns else None,
        "source_file_name": source_file_name,
    })
    return out.groupby(["month", "product_id"], as_index=False).agg({
        "product_name": "first",
        "material_cost": "first",       # 단위당이므로 first (동일 제품은 같은 단가)
        "factory_price": "first",
        "manufacturing_cost": "first",
        "manufacturing_ratio": "first",
        "series_name": "first",
        "source_file_name": "first",
    })


# ── BOM (자재코드+자재색상으로 material_id 구성) ──────────────
def standardize_bom(df: pd.DataFrame, month: str, source_file_name: str) -> pd.DataFrame:
    # product_id: 단품코드+단품컬러
    if "단품컬러" in df.columns:
        product_id = normalize_text(df["단품코드"]).fillna("") + normalize_text(df["단품컬러"]).fillna("")
    else:
        product_id = normalize_text(df["단품코드"])

    # material_id: 자재코드+자재색상 (purchase/inventory와 동일한 키로 직접 매칭)
    mat_code = normalize_text(df["자재코드"])
    if "자재색상" in df.columns:
        mat_color = normalize_text(df["자재색상"])
        material_id = mat_code.fillna("") + mat_color.fillna("")
    else:
        mat_color = None
        material_id = mat_code

    out = pd.DataFrame({
        "month": month,
        "product_id": product_id,
        "material_id": material_id,
        "material_code": mat_code,
        "material_color": mat_color,
        "material_name": normalize_text(df["자재명칭"]),
        "material_group": normalize_text(df["자재구분"]) if "자재구분" in df.columns else None,
        "usage_type": normalize_text(df["사용구분"]) if "사용구분" in df.columns else None,
        "unit_cost": to_number(df["자재단가"]) if "자재단가" in df.columns else None,
        "unit_qty": to_number(df["소요량"]),
        "bom_amount": to_number(df["금액"]) if "금액" in df.columns else None,
        "source_file_name": source_file_name,
    })
    return out.groupby(["month", "product_id", "material_id"], as_index=False).agg({
        "material_code": "first",
        "material_color": "first",
        "material_name": "first",
        "material_group": "first",
        "usage_type": "first",
        "unit_cost": "max",
        "unit_qty": "sum",
        "bom_amount": "sum",
        "source_file_name": "first",
    })


# ── 구매 ─────────────────────────────────────────────────────
def standardize_purchase(df: pd.DataFrame, month: str, source_file_name: str) -> pd.DataFrame:
    # Total/합계 행 제거 (거래처명이 'Total' 이거나 번호가 NaN인 합계행)
    df = df.copy()
    if "거래처명" in df.columns:
        df = df[~df["거래처명"].astype(str).str.strip().str.lower().isin(["total", "합계", "소계"])]
    if "번호" in df.columns:
        df = df[df["번호"].notna() | df["자재명"].notna()]
    df = df.reset_index(drop=True)

    mat_code = normalize_text(df["자재코드"])
    if "색상" in df.columns:
        color = normalize_text(df["색상"])
        material_id = mat_code.fillna("") + color.fillna("")
    else:
        color = None
        material_id = mat_code

    out = pd.DataFrame({
        "month": month,
        "material_id": material_id,
        "material_code": mat_code,
        "material_color": color,
        "material_name": normalize_text(df["자재명"]),
        "vendor_name": normalize_text(df["거래처명"]) if "거래처명" in df.columns else None,
        "purchase_qty": to_number(df["입고량"]),
        "purchase_amount": to_number(df["입고금액"]),
        "account_type": normalize_text(df["계정구분"]) if "계정구분" in df.columns else None,
        "source_file_name": source_file_name,
    })
    return out.groupby(["month", "material_id", "vendor_name"], as_index=False).agg({
        "material_code": "first",
        "material_color": "first",
        "material_name": "first",
        "purchase_qty": "sum",
        "purchase_amount": "sum",
        "account_type": "first",
        "source_file_name": "first",
    })


# ── 기초재고 ──────────────────────────────────────────────────
def standardize_inventory_begin(df: pd.DataFrame, month: str, source_file_name: str) -> pd.DataFrame:
    mat_code = normalize_text(df["자재코드"])
    if "색상" in df.columns:
        color = normalize_text(df["색상"].astype(str))
        material_id = mat_code.fillna("") + color.fillna("")
    else:
        color = None
        material_id = mat_code

    out = pd.DataFrame({
        "month": month,
        "material_id": material_id,
        "material_code": mat_code,
        "material_color": color,
        "material_name": normalize_text(df["자재명"]),
        "begin_qty": to_number(df["현재고"]),
        "begin_amount": to_number(df["현재고금액"]),
        "avg_unit_cost": to_number(df["총평균단가"]) if "총평균단가" in df.columns else None,
        "unit_name": normalize_text(df["단위"]) if "단위" in df.columns else None,
        "source_file_name": source_file_name,
    })
    return out.groupby(["month", "material_id"], as_index=False).agg({
        "material_code": "first",
        "material_color": "first",
        "material_name": "first",
        "begin_qty": "sum",
        "begin_amount": "sum",
        "avg_unit_cost": "max",
        "unit_name": "first",
        "source_file_name": "first",
    })


# ── 기말재고 ──────────────────────────────────────────────────
def standardize_inventory_end(df: pd.DataFrame, month: str, source_file_name: str) -> pd.DataFrame:
    mat_code = normalize_text(df["자재코드"])
    if "색상" in df.columns:
        color = normalize_text(df["색상"].astype(str))
        material_id = mat_code.fillna("") + color.fillna("")
    else:
        color = None
        material_id = mat_code

    out = pd.DataFrame({
        "month": month,
        "material_id": material_id,
        "material_code": mat_code,
        "material_color": color,
        "material_name": normalize_text(df["자재명"]),
        "end_qty": to_number(df["현재고"]),
        "end_amount": to_number(df["현재고금액"]),
        "avg_unit_cost": to_number(df["총평균단가"]) if "총평균단가" in df.columns else None,
        "unit_name": normalize_text(df["단위"]) if "단위" in df.columns else None,
        "source_file_name": source_file_name,
    })
    return out.groupby(["month", "material_id"], as_index=False).agg({
        "material_code": "first",
        "material_color": "first",
        "material_name": "first",
        "end_qty": "sum",
        "end_amount": "sum",
        "avg_unit_cost": "max",
        "unit_name": "first",
        "source_file_name": "first",
    })


# ── JIT 자재 목록 ─────────────────────────────────────────────
def standardize_jit_materials(df: pd.DataFrame, month: str, source_file_name: str) -> pd.DataFrame:
    code_col = "자재코드"
    color_col = "색상" if "색상" in df.columns else None
    name_col = "자재명" if "자재명" in df.columns else "자재명칭"

    mat_code = normalize_text(df[code_col])
    if color_col:
        color = normalize_text(df[color_col])
        material_id = mat_code.fillna("") + color.fillna("")
    else:
        color = None
        material_id = mat_code

    out = pd.DataFrame({
        "month": month,
        "material_id": material_id,
        "material_code": mat_code,
        "material_color": color,
        "material_name": normalize_text(df[name_col]),
        "vendor_name": normalize_text(df["거래처명"]) if "거래처명" in df.columns else None,
        "unit_cost": to_number(df["자재단가"]) if "자재단가" in df.columns else None,
        "unit": normalize_text(df["단위"]) if "단위" in df.columns else None,
        "order_policy": normalize_text(df["발주방침"]) if "발주방침" in df.columns else None,
        "production_mgmt_no": normalize_text(df["생산관리번호"]) if "생산관리번호" in df.columns else None,
        "source_file_name": source_file_name,
    })
    out = out[out["material_id"].str.strip() != ""]
    out = out.drop_duplicates(subset=["month", "material_id"], keep="first")
    return out.reset_index(drop=True)


TRANSFORMER_MAP = {
    "receipt_performance": standardize_receipt,
    "material_cost": standardize_material_cost,
    "bom": standardize_bom,
    "purchase": standardize_purchase,
    "inventory_begin": standardize_inventory_begin,
    "inventory_end": standardize_inventory_end,
    "jit_materials": standardize_jit_materials,
}
