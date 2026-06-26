"""
SocialPulse - Engagement feature transforms.
Engagement is platform-specific and heavily right-skewed, so all normalization is
done WITHIN each platform; raw scores are never pooled across platforms.
"""

import numpy as np
import pandas as pd


def add_engagement_features(
    df: pd.DataFrame, score_col: str = "Engagement Score", platform_col: str = "Platform"
) -> pd.DataFrame:
    """Add engagement_raw/log/pct_within_platform/high/tier columns."""
    df = df.copy()
    raw = pd.to_numeric(df[score_col], errors="coerce").fillna(0)
    raw = raw.clip(lower=0)  # clip -1 'unavailable' sentinels to 0
    df["engagement_raw"] = raw
    df["engagement_log"] = np.log1p(raw)
    df["engagement_pct_within_platform"] = (
        raw.groupby(df[platform_col]).rank(pct=True).round(4)
    )
    df["engagement_high"] = (df["engagement_pct_within_platform"] >= 0.75).astype(int)

    def _tier(group: pd.Series) -> pd.Series:
        med = group[group > 0].median()
        out = pd.Series("none", index=group.index)
        nonzero = group > 0
        out[nonzero & (group < med)] = "med"
        out[nonzero & (group >= med)] = "high"
        return out

    df["engagement_tier"] = raw.groupby(df[platform_col], group_keys=False).apply(_tier)
    return df
