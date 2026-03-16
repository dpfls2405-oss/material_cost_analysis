from __future__ import annotations

import os
import streamlit as st

DATASET_TYPES = [
    "receipt_performance",
    "material_cost",
    "bom",
    "purchase",
    "inventory_begin",
    "inventory_end",
    "jit_materials",
]

DISPLAY_NAMES = {
    "receipt_performance": "입고실적",
    "material_cost": "재료비",
    "bom": "월별 BOM",
    "purchase": "구매",
    "inventory_begin": "기초재고",
    "inventory_end": "기말재고",
    "jit_materials": "JIT 자재 목록",
}

TABLE_MAP = {
    "receipt_performance": "receipt_performance",
    "material_cost": "material_cost",
    "bom": "bom_monthly",
    "purchase": "purchase",
    "inventory_begin": "inventory_begin",
    "inventory_end": "inventory_end",
    "jit_materials": "jit_materials",
}


def get_secret(name: str, default: str = "") -> str:
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.getenv(name, default)


def supabase_enabled() -> bool:
    return bool(get_secret("SUPABASE_URL") and get_secret("SUPABASE_KEY"))
