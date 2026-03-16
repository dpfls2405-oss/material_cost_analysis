from __future__ import annotations

import pandas as pd
from helpers import parse_filename

REQUIRED_COLUMNS = {
    "receipt_performance": ["단품코드", "단품명", "입고수량", "입고금액"],
    "material_cost": ["코드", "단품명칭", "총자재비"],
    "bom": ["단품코드", "자재코드", "자재명칭", "소요량"],
    "purchase": ["자재코드", "자재명", "입고량", "입고금액"],
    "inventory_begin": ["자재코드", "자재명", "현재고", "현재고금액"],
    "inventory_end": ["자재코드", "자재명", "현재고", "현재고금액"],
    "jit_materials": ["자재코드", "색상", "자재명"],
}

KEY_COLUMNS = {
    "receipt_performance": ["단품코드"],
    "material_cost": ["코드"],
    "bom": ["단품코드", "자재코드"],
    "purchase": ["자재코드"],
    "inventory_begin": ["자재코드"],
    "inventory_end": ["자재코드"],
    "jit_materials": ["자재코드"],
}


def validate_filename(file_name: str) -> tuple[str, str]:
    return parse_filename(file_name)


def validate_required_columns(df: pd.DataFrame, dataset_type: str) -> list[str]:
    return [col for col in REQUIRED_COLUMNS[dataset_type] if col not in df.columns]


def drop_empty_key_rows(df: pd.DataFrame, dataset_type: str) -> tuple[pd.DataFrame, int]:
    """키 컬럼이 비어있는 행(합계행 등) 자동 제거"""
    keys = KEY_COLUMNS.get(dataset_type, [])
    before = len(df)
    for col in keys:
        if col in df.columns:
            df = df[df[col].notna() & (df[col].astype(str).str.strip() != "")]
    return df.reset_index(drop=True), before - len(df)


def summarize_validation(df: pd.DataFrame, dataset_type: str) -> dict:
    missing = validate_required_columns(df, dataset_type)
    if missing:
        return {
            "row_count": len(df),
            "dropped_count": 0,
            "cleaned_df": df,
            "missing_columns": missing,
            "ok": False,
        }

    cleaned, dropped = drop_empty_key_rows(df, dataset_type)
    return {
        "row_count": len(cleaned),
        "dropped_count": dropped,
        "cleaned_df": cleaned,
        "missing_columns": [],
        "ok": True,
    }
