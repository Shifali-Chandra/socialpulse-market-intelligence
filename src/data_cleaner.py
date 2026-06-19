"""
SocialPulse Market Intelligence - Data Cleaner (Platform Agnostic)
Accepts any CSV dataset and auto-detects column types for cleaning.
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
        description="Clean any CSV dataset and save a cleaned version."
    )
    parser.add_argument("input_file", type=Path, help="Path to input CSV file")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/clean"),
        help="Directory for cleaned output (default: data/clean)",
    )
    parser.add_argument(
        "--drop-duplicates", action=argparse.BooleanOptionalAction, default=True,
        help="Drop duplicate rows (use --no-drop-duplicates to disable; default: True)",
    )
    parser.add_argument(
        "--strip-html", action=argparse.BooleanOptionalAction, default=True,
        help="Strip HTML tags from text columns (use --no-strip-html to disable; default: True)",
    )
    parser.add_argument(
        "--clean-social-text", action=argparse.BooleanOptionalAction, default=True,
        help="Remove URLs/mentions/hashtag symbols and normalize whitespace in text "
             "columns (use --no-clean-social-text to disable; default: True)",
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


def _strip_html_tags(text: str) -> str:
    """Remove HTML tags from a string."""
    return re.sub(r"<[^>]+>", "", str(text)).strip()


# Pre-compiled patterns (compiled once, reused per cell — faster on large datasets).
_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_MENTION_RE = re.compile(r"@\w+")
_HASHTAG_SYMBOL_RE = re.compile(r"#(?=\w)")
_WHITESPACE_RE = re.compile(r"\s+")


def _clean_social_text(text: str) -> str:
    """Normalize social-media text: drop URLs and @mentions, strip the '#'
    symbol while keeping the hashtag word, and collapse whitespace.

    Note: casing is intentionally preserved — modern sentiment/transformer
    models use it, and lowercasing can always be applied later if needed.
    """
    text = _URL_RE.sub(" ", str(text))
    text = _MENTION_RE.sub(" ", text)
    text = _HASHTAG_SYMBOL_RE.sub("", text)  # "#AI" -> "AI", keeps the topic word
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def clean_dataset(df: pd.DataFrame, col_types: dict, args: argparse.Namespace) -> pd.DataFrame:
    """Apply cleaning operations and log each step."""
    original_count = len(df)
    df = df.copy()
    logger.info("Starting cleaning (%d rows)...", original_count)

    # 1. Drop duplicates
    if args.drop_duplicates:
        before = len(df)
        df = df.drop_duplicates()
        removed = before - len(df)
        if removed:
            logger.info("Dropped %d duplicate rows.", removed)
        else:
            logger.info("No duplicate rows found.")

    # 2. Strip whitespace from all string columns
    for c in df.select_dtypes(include=["object", "string"]).columns:
        df[c] = df[c].astype(str).str.strip()

    # 3. Strip HTML from text columns
    if args.strip_html and col_types["text"]:
        for c in col_types["text"]:
            before_nulls = df[c].isna().sum()
            df[c] = df[c].apply(_strip_html_tags)
            df[c] = df[c].replace("", pd.NA)
            after_nulls = df[c].isna().sum()
            if after_nulls > before_nulls:
                logger.info(
                    "Stripped HTML from '%s' (%d rows became empty → marked as NA).", c, after_nulls - before_nulls
                )

    # 3b. Normalize social-media text (URLs, mentions, hashtag symbols, whitespace)
    if args.clean_social_text and col_types["text"]:
        for c in col_types["text"]:
            before_nulls = df[c].isna().sum()
            mask = df[c].notna()
            df.loc[mask, c] = df.loc[mask, c].apply(_clean_social_text)
            df[c] = df[c].replace("", pd.NA)
            after_nulls = df[c].isna().sum()
            logger.info("Normalized social text in '%s'.", c)
            if after_nulls > before_nulls:
                logger.info(
                    "  '%s': %d rows became empty after normalization → marked as NA.",
                    c, after_nulls - before_nulls,
                )

    # 4. Handle missing values
    if col_types["id"]:
        before = len(df)
        df = df.dropna(subset=col_types["id"])
        dropped = before - len(df)
        if dropped:
            logger.info("Dropped %d rows missing ID values.", dropped)

    for c in col_types["text"]:
        nulls = df[c].isna().sum()
        if nulls:
            df[c] = df[c].fillna("")
            logger.info("Filled %d nulls in text column '%s'.", nulls, c)

    for c in col_types["numeric"]:
        nulls = df[c].isna().sum()
        if nulls:
            df[c] = df[c].fillna(0)
            logger.info("Filled %d nulls in numeric column '%s'.", nulls, c)

    # 5. Standardize date columns to YYYY-MM-DD
    for c in col_types["date"]:
        try:
            parsed = pd.to_datetime(df[c], errors="coerce")
            df[c] = parsed.dt.strftime("%Y-%m-%d")
            logger.info("Standardized date column '%s' to YYYY-MM-DD.", c)
        except Exception:
            logger.warning("Could not parse dates in column '%s'.", c)

    removed_count = original_count - len(df)
    logger.info(
        "Cleaning complete. Rows: %d → %d (removed %d).", original_count, len(df), removed_count
    )
    return df


def _derive_platform(input_file: Path) -> str:
    stem = input_file.stem
    match = re.match(r"^([a-zA-Z0-9_]+?)(?:_master_dataset|_dataset|_cleaned|$)", stem)
    if match:
        return match.group(1).lower().replace(" ", "_")
    return stem.lower().replace(" ", "_")


def save_clean(df: pd.DataFrame, input_path: Path, output_dir: Path) -> Path:
    platform = _derive_platform(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{platform}_cleaned.csv"
    try:
        df.to_csv(out_path, index=False, encoding="utf-8-sig")
        logger.info("Cleaned dataset saved: %s", out_path)
    except Exception as e:
        logger.error("Failed to save cleaned dataset: %s", e)
        sys.exit(1)
    return out_path


def main() -> None:
    args = parse_args()
    logger.info("Starting data cleaning for: %s", args.input_file)

    df = load_dataset(args.input_file)
    col_types = _classify_columns(df)

    logger.info("Detected column types: %s", col_types)

    cleaned = clean_dataset(df, col_types, args)
    save_clean(cleaned, args.input_file, args.output_dir)

    logger.info("Data cleaning complete.")


if __name__ == "__main__":
    main()
