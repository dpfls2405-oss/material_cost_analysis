from __future__ import annotations

import streamlit as st
import pandas as pd

from config import DISPLAY_NAMES, DATASET_TYPES, supabase_enabled
from helpers import read_csv_flexible, parse_filename
from validator import summarize_validation
from transformers import TRANSFORMER_MAP
from supabase_client import upsert_dataframe, insert_upload_log

st.title("📥 CSV 업로드")
st.caption("형식 검증 후 Supabase에 적재합니다. 파일명: YYYY-MM_dataset.csv")

uploaded_files = st.file_uploader(
    "파일 선택",
    type=["csv"],
    accept_multiple_files=True,
    help="예: 2026-02_receipt_performance.csv",
)

if not supabase_enabled():
    st.warning("Supabase secrets가 없어 저장은 비활성화됩니다. 미리보기와 검증만 가능합니다.")

if uploaded_files:
    for uploaded_file in uploaded_files:
        st.divider()
        st.subheader(uploaded_file.name)
        try:
            month, dataset_type = parse_filename(uploaded_file.name)
            if dataset_type not in DATASET_TYPES:
                raise ValueError(f"지원하지 않는 dataset 타입: {dataset_type}")

            raw = read_csv_flexible(uploaded_file)
            summary = summarize_validation(raw, dataset_type)

            st.write(f"- 월: `{month}` / 유형: `{DISPLAY_NAMES[dataset_type]}` / 행 수: `{summary['row_count']}`")

            if summary.get("dropped_count", 0) > 0:
                st.info(f"ℹ️ 키 값이 없는 행(합계행 등) {summary['dropped_count']}건 자동 제거됨")

            if not summary["ok"]:
                st.error("검증 실패")
                if summary["missing_columns"]:
                    st.write("누락 컬럼:", summary["missing_columns"])
                if supabase_enabled():
                    insert_upload_log(month, dataset_type, uploaded_file.name, len(raw), "FAILED", str(summary))
                continue

            cleaned_raw = summary["cleaned_df"]
            standardized = TRANSFORMER_MAP[dataset_type](cleaned_raw, month, uploaded_file.name)
            st.success(f"✅ 검증 통과 — {len(standardized)}행 표준화 완료")

            with st.expander("표준화 미리보기 (상위 10행)"):
                st.dataframe(standardized.head(10), use_container_width=True)

            if supabase_enabled():
                if st.button(f"💾 {uploaded_file.name} 저장", key=f"save_{uploaded_file.name}"):
                    try:
                        upsert_dataframe(dataset_type, standardized)
                        insert_upload_log(month, dataset_type, uploaded_file.name, len(standardized), "SUCCESS")
                        st.success("Supabase 저장 완료")
                    except Exception as exc:
                        insert_upload_log(month, dataset_type, uploaded_file.name, len(standardized), "FAILED", str(exc))
                        st.error(f"저장 실패: {exc}")
        except Exception as exc:
            st.error(f"처리 실패: {exc}")
