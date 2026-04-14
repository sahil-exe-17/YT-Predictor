"""
insights.py — Growth insights, consistency scoring, viral detection.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


# ─────────────────────────────────────────────
# Upload consistency score
# ─────────────────────────────────────────────

def consistency_score(videos_df: pd.DataFrame) -> dict:
    """
    Score 0-100 based on upload regularity.
    Penalises long gaps between uploads.
    """
    if videos_df.empty or len(videos_df) < 3:
        return {"score": 0, "label": "Unknown", "avg_gap_days": None, "std_gap_days": None}

    df = videos_df.sort_values("published_at").copy()
    df["published_at"] = pd.to_datetime(df["published_at"])

    gaps = df["published_at"].diff().dt.days.dropna()
    avg_gap = gaps.mean()
    std_gap = gaps.std()

    # Coefficient of variation (lower = more consistent)
    cv = std_gap / avg_gap if avg_gap > 0 else 1.0
    raw_score = max(0, 100 - cv * 50 - (avg_gap / 7) * 5)
    score = int(np.clip(raw_score, 0, 100))

    if score >= 80:
        label = "🟢 Very Consistent"
    elif score >= 55:
        label = "🟡 Moderate"
    elif score >= 30:
        label = "🟠 Irregular"
    else:
        label = "🔴 Inconsistent"

    return {
        "score": score,
        "label": label,
        "avg_gap_days": round(avg_gap, 1),
        "std_gap_days": round(std_gap, 1),
    }


# ─────────────────────────────────────────────
# Best upload day analysis
# ─────────────────────────────────────────────

def best_upload_day(videos_df: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame of day → avg_views, avg_engagement sorted by performance."""
    if videos_df.empty:
        return pd.DataFrame()

    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    df = videos_df.copy()
    df["publish_day"] = pd.Categorical(df["publish_day"], categories=day_order, ordered=True)

    grp = df.groupby("publish_day", observed=True).agg(
        num_videos   =("video_id", "count"),
        avg_views    =("views", "mean"),
        avg_likes    =("likes", "mean"),
        avg_comments =("comments", "mean"),
        avg_engagement=("engagement_score", "mean"),
    ).reset_index()

    grp["avg_views"]     = grp["avg_views"].round(0).astype(int)
    grp["avg_likes"]     = grp["avg_likes"].round(0).astype(int)
    grp["avg_comments"]  = grp["avg_comments"].round(0).astype(int)
    grp["avg_engagement"]= grp["avg_engagement"].round(0).astype(int)
    return grp.sort_values("avg_engagement", ascending=False)


# ─────────────────────────────────────────────
# Viral video detector
# ─────────────────────────────────────────────

def detect_viral_videos(videos_df: pd.DataFrame, z_threshold: float = 1.8) -> pd.DataFrame:
    """
    Flag videos whose view / engagement score is > z_threshold std deviations
    above the channel mean.
    """
    if videos_df.empty or len(videos_df) < 5:
        return pd.DataFrame()

    df = videos_df.copy()
    mean_eng = df["engagement_score"].mean()
    std_eng  = df["engagement_score"].std()

    if std_eng == 0:
        return pd.DataFrame()

    df["z_score"] = (df["engagement_score"] - mean_eng) / std_eng
    viral = df[df["z_score"] >= z_threshold].copy()
    viral["viral_label"] = viral["z_score"].apply(lambda z:
        "🔥 Mega Viral" if z >= 3.5 else ("🚀 Viral" if z >= 2.5 else "⚡ Trending")
    )
    return viral.sort_values("z_score", ascending=False).reset_index(drop=True)


# ─────────────────────────────────────────────
# Plateau / slowdown warning
# ─────────────────────────────────────────────

def plateau_warning(history_df: pd.DataFrame, window_weeks: int = 8) -> dict:
    """
    Detect if recent growth rate is significantly lower than historical average.
    Returns dict with warning flag, recent rate, historical rate.
    """
    if history_df.empty or "growth_rate_weekly" not in history_df.columns:
        return {"is_plateau": False, "recent_rate": None, "historical_rate": None, "message": ""}

    rates = history_df["growth_rate_weekly"].dropna()
    if len(rates) < window_weeks + 4:
        return {"is_plateau": False, "recent_rate": None, "historical_rate": None, "message": ""}

    recent_rate     = rates.iloc[-window_weeks:].mean()
    historical_rate = rates.iloc[:-window_weeks].mean()

    is_plateau = (
        historical_rate > 0.01 and
        recent_rate < historical_rate * 0.4
    )

    if is_plateau:
        pct_drop = ((historical_rate - recent_rate) / historical_rate) * 100
        message = (
            f"⚠️ Growth has slowed by **{pct_drop:.0f}%** compared to historical average. "
            f"Recent weekly growth: **{recent_rate:.2f}%** vs historical **{historical_rate:.2f}%**."
        )
    else:
        message = f"✅ Growth appears healthy. Weekly avg: **{recent_rate:.2f}%**."

    return {
        "is_plateau":       is_plateau,
        "recent_rate":      round(recent_rate, 3),
        "historical_rate":  round(historical_rate, 3),
        "message":          message,
    }


# ─────────────────────────────────────────────
# Competitor comparison helper
# ─────────────────────────────────────────────

def compare_channels(ch_a: dict, ch_b: dict) -> pd.DataFrame:
    """Build a simple comparison DataFrame for two channel info dicts."""
    metrics = ["subscribers", "total_views", "video_count", "age_days"]
    labels  = ["Subscribers", "Total Views", "Videos", "Channel Age (days)"]

    rows = []
    for m, lbl in zip(metrics, labels):
        rows.append({
            "Metric": lbl,
            ch_a["title"]: ch_a.get(m, 0),
            ch_b["title"]: ch_b.get(m, 0),
        })

    df = pd.DataFrame(rows)

    # Derive views-per-video
    vpv_a = ch_a["total_views"] / max(ch_a["video_count"], 1)
    vpv_b = ch_b["total_views"] / max(ch_b["video_count"], 1)
    df.loc[len(df)] = {"Metric": "Views per Video", ch_a["title"]: int(vpv_a), ch_b["title"]: int(vpv_b)}

    # Subs per video
    spv_a = ch_a["subscribers"] / max(ch_a["video_count"], 1)
    spv_b = ch_b["subscribers"] / max(ch_b["video_count"], 1)
    df.loc[len(df)] = {"Metric": "Subs per Video", ch_a["title"]: round(spv_a, 1), ch_b["title"]: round(spv_b, 1)}

    return df
# ─────────────────────────────────────────────
# Strategic Advisory (The JARVIS touch)
# ─────────────────────────────────────────────

def generate_strategic_advisory(vids_df: pd.DataFrame, hist_df: pd.DataFrame) -> list:
    """
    Generate high-level, actionable strategy points based on channel performance.
    Returns a list of dicts with {level: 'good'|'warn'|'info', text: str}.
    """
    advice = []
    
    # 1. Consistency Check
    cs = consistency_score(vids_df)
    if cs["score"] < 40:
        advice.append({
            "level": "warn",
            "text": f"**Urgent: Establish Rhythm.** Your upload consistency is currently at {cs['score']}%. The algorithm prioritizes predictability. Aim for a fixed schedule even if it's less frequent."
        })
    elif cs["score"] > 80:
        advice.append({
            "level": "good",
            "text": "**Momentum Secured.** Your consistency is excellent. This stability allows you to experiment with 'high-risk' content without losing your core audience."
        })

    # 2. Viral Potential
    viral = detect_viral_videos(vids_df)
    if not viral.empty:
        best_viral = viral.iloc[0]
        advice.append({
            "level": "info",
            "text": f"**Double Down:** Your video *'{best_viral['title'][:40]}...' habituated viral growth.* Analyze its first 30 seconds—replicate that hook in your next 3 uploads."
        })
    
    # 3. Growth Plateau
    pw = plateau_warning(hist_df)
    if pw["is_plateau"]:
        advice.append({
            "level": "warn",
            "text": "**System Alert: Stagnation Detected.** Your growth velocity has dropped significantly. It is time to pivot your thumbnail style or explore a trending sub-topic to break the ceiling."
        })
    else:
        advice.append({
            "level": "good",
            "text": "**Growth trajectory is optimal.** You are currently outperforming your historical averages. Stay the course."
        })

    # 4. Best Day
    best_day_df = best_upload_day(vids_df)
    if not best_day_df.empty:
        best_day = best_day_df.iloc[0]["publish_day"]
        advice.append({
            "level": "info",
            "text": f"**Tactical Window:** Your audience is most responsive on **{best_day}s**. Schedule your 'hero' content strictly for this window for maximum impact."
        })

    # Default if empty
    if not advice:
        advice.append({"level": "info", "text": "Analyzing data... continue uploading to generate deeper strategic directives."})
        
    return advice
