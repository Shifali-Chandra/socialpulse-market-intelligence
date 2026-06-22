"""Incremental, deduplicated append for daily collection (new-content-only)."""

from datetime import date
from pathlib import Path

import pandas as pd


def save_incremental(new_rows, output_file, key_cols):
    """Append new rows to the master CSV and drop duplicates on key_cols."""
    new_df = pd.DataFrame(new_rows)
    if new_df.empty:
        print("No rows collected, nothing to save.")
        return
    for k in key_cols:
        new_df[k] = new_df[k].astype(str)
    new_df["Collected At"] = date.today().isoformat()

    path = Path(output_file)
    if path.exists():
        existing = pd.read_csv(path, dtype={k: str for k in key_cols})
        prior = len(existing)
        combined = pd.concat([existing, new_df], ignore_index=True)
    else:
        prior = 0
        combined = new_df

    combined = combined.drop_duplicates(subset=key_cols, keep="first")
    added = len(combined) - prior
    path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"Fetched {len(new_df)}, new after dedup: {added}, total: {len(combined)}")
