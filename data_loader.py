from __future__ import annotations

from pathlib import Path
import pandas as pd
from helpers import parse_filename
from transformers import TRANSFORMER_MAP
from config import supabase_enabled

LOCAL_DATA_DIR = Path("data")

_DATASET_KEYS = [
    "receipt_performance",
    "material_cost",
    "bom",
    "purchase",
    "inventory_begin",
    "inventory_end",
    "jit_materials",
]


def _empty_dataset() -> dict[str, pd.DataFrame]:
    return {k: pd.DataFrame() for k in _DATASET_KEYS}


def load_local_raw_files() -> dict[str, pd.DataFrame]:
    if not LOCAL_DATA_DIR.exists():
        return _empty_dataset()
    result: dict[str, list[pd.DataFrame]] = {}
    for path in LOCAL_DATA_DIR.glob("*.csv"):
        try:
            month, dataset_type = parse_filename(path.name)
            for enc in ["utf-8-sig", "cp949", "euc-kr"]:
                try:
                    raw = pd.read_csv(path, encoding=enc)
                    break
                except Exception:
                    continue
            else:
                continue
            std = TRANSFORMER_MAP[dataset_type](raw, month, path.name)
            result.setdefault(dataset_type, []).append(std)
        except Exception:
            continue
    merged = {k: pd.concat(v, ignore_index=True) for k, v in result.items()}
    for k in _DATASET_KEYS:
        merged.setdefault(k, pd.DataFrame())
    return merged


def load_standardized_data() -> dict[str, pd.DataFrame]:
    if supabase_enabled():
        try:
            from supabase_client import fetch_table
            return {
                "receipt_performance": fetch_table("receipt_performance"),
                "material_cost": fetch_table("material_cost"),
                "bom": fetch_table("bom_monthly"),
                "purchase": fetch_table("purchase"),
                "inventory_begin": fetch_table("inventory_begin"),
                "inventory_end": fetch_table("inventory_end"),
                "jit_materials": fetch_table("jit_materials"),
            }
        except Exception as e:
            import streamlit as st
            st.warning(f"⚠️ Supabase 연결 실패: {e}")
            return _empty_dataset()
    return load_local_raw_files()
