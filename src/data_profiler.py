"""
SocialPulse Market Intelligence - Data Profiler (Platform Agnostic)
Accepts any CSV dataset via CLI and auto-detects column types for profiling.
"""

import argparse
import io
import logging
import re
import sys
from pathlib import Path

import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Profile any CSV dataset and generate a report."
    )
    parser.add_argument("input_file", type=Path, help="Path to input CSV file")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/reports"),
        help="Directory for output files (default: data/reports)",
    )
    return parser.parse_args()


def _normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Strip surrounding whitespace from column names."""
    renamed = {c: c.strip() for c in df.columns if c != c.strip()}
    if renamed:
        df = df.rename(columns=renamed)
        logger.info("Normalized %d column name(s): %s", len(renamed), list(renamed.values()))
    return df


def load_dataset(filepath: Path) -> pd.DataFrame:
    if not filepath.exists():
        logger.error("File not found: %s", filepath)
        sys.exit(1)
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            df = pd.read_csv(filepath, encoding=encoding)
            if encoding != "utf-8":
                logger.warning("Read using fallback encoding '%s' (not UTF-8).", encoding)
            df = _normalize_column_names(df)
            logger.info("Loaded: %s (rows=%d, cols=%d)", filepath, len(df), len(df.columns))
            return df
        except UnicodeDecodeError:
            continue
        except Exception as e:
            logger.error("Failed to load dataset: %s", e)
            sys.exit(1)
    logger.error("Failed to load dataset: could not decode with utf-8/cp1252/latin-1.")
    sys.exit(1)


def _classify_columns(df: pd.DataFrame) -> dict:
    """Auto-detect column roles without hardcoded names."""
    numeric_cols = list(df.select_dtypes(include="number").columns)

    text_cols = []
    category_cols = []
    id_cols = []
    author_cols = []
    date_cols = []

    for c in df.columns:
        if pd.api.types.is_string_dtype(df[c]) or df[c].dtype == object:
            lower = c.lower().replace(" ", "_").replace("-", "_")
            if re.search(r"(^|_)id(_|$)", lower) or lower.endswith("id"):
                id_cols.append(c)
            elif re.search(r"author|user|creator", lower):
                author_cols.append(c)
            elif re.search(r"date|time|timestamp|published|created", lower):
                date_cols.append(c)
            else:
                nunique = df[c].nunique()
                if nunique < len(df) * 0.3 and nunique < 100:
                    category_cols.append(c)
                else:
                    text_cols.append(c)
        elif pd.api.types.is_bool_dtype(df[c]):
            category_cols.append(c)
        elif pd.api.types.is_numeric_dtype(df[c]):
            if c not in numeric_cols:
                numeric_cols.append(c)

    return {
        "numeric": numeric_cols,
        "text": text_cols,
        "category": category_cols,
        "id": id_cols,
        "author": author_cols,
        "date": date_cols,
    }


def _derive_platform(input_file: Path) -> str:
    """Extract platform name from filename (e.g. 'youtube_master_dataset' → 'youtube')."""
    stem = input_file.stem
    match = re.match(r"^([a-zA-Z0-9_]+?)(?:_master_dataset|_dataset|_cleaned|$)", stem)
    if match:
        return match.group(1).lower().replace(" ", "_")
    return stem.lower().replace(" ", "_")


def _derive_stage(input_file: Path) -> str:
    """Return 'clean' if the filename marks cleaned data, else 'raw'."""
    return "clean" if "clean" in input_file.stem.lower() else "raw"


def generate_profile(df: pd.DataFrame, col_types: dict) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append("SOCIALPULSE — DATA PROFILE REPORT")
    lines.append("=" * 60)
    lines.append(f"Total records: {len(df)}")
    lines.append(f"Total columns: {len(df.columns)}")
    lines.append(f"Column names: {', '.join(df.columns)}")
    lines.append("")

    lines.append("--- Column Types (auto-detected) ---")
    for role, cols in col_types.items():
        lines.append(f"  {role}: {cols if cols else '—'}")
    lines.append("")

    lines.append("--- Missing Values ---")
    missing = df.isnull().sum()
    missing = missing[missing > 0]
    if len(missing):
        lines.append(f"  {missing.to_string()}")
    else:
        lines.append("  None")
    lines.append("")
    lines.append(f"Duplicate row count: {df.duplicated().sum()}")
    lines.append("")

    for col in col_types["category"]:
        lines.append(f"Unique values in '{col}': {df[col].nunique()}")
    lines.append("")

    lines.append("--- Numeric Statistics ---")
    if col_types["numeric"]:
        desc = df[col_types["numeric"]].describe().round(2)
        for col in col_types["numeric"]:
            lines.append(f"  {col}:")
            for stat in ["count", "mean", "std", "min", "25%", "50%", "75%", "max"]:
                lines.append(f"    {stat}: {desc.loc[stat, col]}")
    else:
        lines.append("  None")
    lines.append("")

    lines.append("--- Text Statistics ---")
    if col_types["text"]:
        for col in col_types["text"]:
            lengths = df[col].astype(str).str.len()
            lines.append(f"  {col}:")
            lines.append(f"    Avg length: {lengths.mean():.2f} chars")
            lines.append(f"    Min length: {lengths.min()} chars")
            lines.append(f"    Max length: {lengths.max()} chars")
    else:
        lines.append("  None")

    lines.append("=" * 60)
    return "\n".join(lines)


def _build_profile_csv(df: pd.DataFrame, col_types: dict) -> pd.DataFrame:
    """Build a structured CSV (Metric / Value) from the profile data."""
    rows = []

    def add(metric, value):
        rows.append({"Metric": metric, "Value": value})

    add("Total Records", len(df))
    add("Total Columns", len(df.columns))
    add("Column Names", ", ".join(df.columns))
    add("", "")
    add("--- Column Types ---", "")
    for role, cols in col_types.items():
        add(role, ", ".join(cols) if cols else "—")
    add("", "")
    add("--- Missing Values ---", "")
    missing = df.isnull().sum()
    missing = missing[missing > 0]
    if len(missing):
        for col, count in missing.items():
            add(f"  Missing: {col}", count)
    else:
        add("Missing Values", "None")
    add("Duplicate Row Count", df.duplicated().sum())
    add("", "")
    add("--- Category Distributions ---", "")
    for col in col_types["category"]:
        add(f"[{col}] unique values", df[col].nunique())
        for val, cnt in df[col].value_counts().head(20).items():
            add(f"  {val}", cnt)
    add("", "")
    add("--- Numeric Statistics ---", "")
    if col_types["numeric"]:
        for col in col_types["numeric"]:
            s = df[col]
            add(f"  Mean ({col})", round(s.mean(), 2))
            add(f"  Std ({col})", round(s.std(), 2))
            add(f"  Min ({col})", s.min())
            add(f"  25% ({col})", s.quantile(0.25))
            add(f"  50% ({col})", s.quantile(0.50))
            add(f"  75% ({col})", s.quantile(0.75))
            add(f"  Max ({col})", s.max())
    else:
        add("Numeric Columns", "None")
    add("", "")
    add("--- Text Statistics ---", "")
    if col_types["text"]:
        for col in col_types["text"]:
            lengths = df[col].astype(str).str.len()
            add(f"  Avg length ({col})", f"{lengths.mean():.2f} chars")
            add(f"  Min length ({col})", f"{lengths.min()} chars")
            add(f"  Max length ({col})", f"{lengths.max()} chars")
    else:
        add("Text Columns", "None")

    return pd.DataFrame(rows)


def save_profile_csv(df_profile: pd.DataFrame, filepath: Path) -> None:
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        df_profile.to_csv(filepath, index=False, encoding="utf-8-sig")
        logger.info("Profile CSV saved: %s", filepath)
    except Exception as e:
        logger.error("Failed to save profile CSV: %s", e)


def main() -> None:
    args = parse_args()
    logger.info("Starting data profiling for: %s", args.input_file)

    df = load_dataset(args.input_file)
    col_types = _classify_columns(df)

    report = generate_profile(df, col_types)
    print("\n" + report)

    platform = _derive_platform(args.input_file)
    stage = _derive_stage(args.input_file)
    subfolder = args.output_dir / platform
    subfolder.mkdir(parents=True, exist_ok=True)

    df_profile = _build_profile_csv(df, col_types)
    save_profile_csv(df_profile, subfolder / f"{platform}_{stage}_profile_report.csv")

    logger.info("Data profiling complete.")


if __name__ == "__main__":
    main()
