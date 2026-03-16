from __future__ import annotations

import math
import pandas as pd
from config import get_secret, TABLE_MAP


def get_client():
    try:
        from supabase import create_client
    except ImportError as exc:
        raise ImportError("supabase-py is not installed. Add `supabase>=2.7` to requirements.txt.") from exc
    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("Supabase secrets are not configured.")
    return create_client(url, key)


def _sanitize_records(records: list[dict]) -> list[dict]:
    sanitized = []
    for row in records:
        clean = {}
        for k, v in row.items():
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                clean[k] = None
            else:
                clean[k] = v
        sanitized.append(clean)
    return sanitized


def upsert_dataframe(dataset_type: str, df: pd.DataFrame) -> None:
    client = get_client()
    table_name = TABLE_MAP[dataset_type]
    records = df.where(pd.notna(df), None).to_dict("records")
    records = _sanitize_records(records)
    if not records:
        return

    on_conflict_map = {
        "receipt_performance": "month,product_id",
        "material_cost": "month,product_id",
        "bom_monthly": "month,product_id,material_id",
        "purchase": "month,material_id,vendor_name",
        "inventory_begin": "month,material_id",
        "inventory_end": "month,material_id",
        "jit_materials": "month,material_id",
    }
    on_conflict = on_conflict_map.get(table_name)

    chunk_size = 500
    for i in range(0, len(records), chunk_size):
        q = client.table(table_name)
        if on_conflict:
            q = q.upsert(records[i:i + chunk_size], on_conflict=on_conflict)
        else:
            q = q.upsert(records[i:i + chunk_size])
        q.execute()


def insert_upload_log(month, dataset_type, source_file_name, row_count, status, message=""):
    client = get_client()
    client.table("upload_log").insert({
        "data_month": month,
        "dataset_type": dataset_type,
        "source_file_name": source_file_name,
        "row_count": row_count,
        "status": status,
        "message": message,
    }).execute()


def fetch_table(table_name: str, columns: str = "*") -> pd.DataFrame:
    client = get_client()
    all_data = []
    offset = 0
    page_size = 1000
    while True:
        result = (
            client.table(table_name)
            .select(columns)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = result.data or []
        all_data.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return pd.DataFrame(all_data)
