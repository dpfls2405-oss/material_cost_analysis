from __future__ import annotations

import re
from io import BytesIO
import pandas as pd

MONTH_PATTERN = re.compile(r"^(\d{4}-\d{2})_([a-z_]+)\.csv$")


def parse_filename(file_name: str) -> tuple[str, str]:
    match = MONTH_PATTERN.match(file_name)
    if not match:
        raise ValueError("파일명은 YYYY-MM_dataset.csv 형식이어야 합니다.")
    return match.group(1), match.group(2)


def read_csv_flexible(uploaded_file) -> pd.DataFrame:
    raw = uploaded_file.getvalue()
    for encoding in ["utf-8-sig", "cp949", "euc-kr", "utf-8"]:
        try:
            return pd.read_csv(BytesIO(raw), encoding=encoding)
        except Exception:
            continue
    return pd.read_csv(BytesIO(raw), engine="python")


def to_number(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    s = s.replace({"": None, "nan": None, "None": None})
    s = s.str.replace(",", "", regex=False)
    s = s.str.replace("%", "", regex=False)
    return pd.to_numeric(s, errors="coerce")


def pct_to_float(series: pd.Series) -> pd.Series:
    return to_number(series) / 100.0


def normalize_text(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().replace({"nan": None, "None": None, "": None})


def fmt_krw(value) -> str:
    """Format number as Korean Won."""
    if pd.isna(value):
        return "-"
    return f"{value:,.0f}"


def fmt_pct(value) -> str:
    """Format number as percentage."""
    if pd.isna(value):
        return "-"
    return f"{value:.2%}"
