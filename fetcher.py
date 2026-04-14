"""
fetcher.py — YouTube Data API v3 calls
Handles all API interactions and returns clean Pandas DataFrames.
"""

import os
import re
import json
import streamlit as st
import pandas as pd
import numpy as np
import requests
import scrapetube
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _parse_channel_input(raw: str) -> str:
    """Accept channel ID, handle or full URL → return channel ID / handle."""
    raw = raw.strip()
    # Already a channel ID (UCxxxxxxxx)
    if re.match(r"^UC[\w-]{22}$", raw):
        return raw
    # URL patterns
    patterns = [
        r"youtube\.com/channel/(UC[\w-]{22})",
        r"youtube\.com/@([\w.-]+)",
        r"youtube\.com/user/([\w.-]+)",
        r"youtube\.com/c/([\w.-]+)",
    ]
    for p in patterns:
        m = re.search(p, raw)
        if m:
            return m.group(1)
    return raw  # return as-is (might be a handle without @)


def _build_service(api_key: str):
    return build("youtube", "v3", developerKey=api_key, cache_discovery=False)


def _iso_to_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


# ─────────────────────────────────────────────
# Keyless (Scraping) Helpers
# ─────────────────────────────────────────────

def _fetch_channel_via_scraping(channel_input: str) -> dict | None:
    """Fallback fetcher when no API key is provided."""
    try:
        parsed = _parse_channel_input(channel_input)
        if parsed.startswith("UC"):
            url = f"https://www.youtube.com/channel/{parsed}/videos"
        else:
            url = f"https://www.youtube.com/@{parsed.lstrip('@')}/videos"

        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}, timeout=10)
        if res.status_code != 200:
            return None

        html = res.text
        # Look for ytInitialData JSON
        m = re.search(r"var ytInitialData = (\{.+?\});", html)
        if not m:
            return None
        
        data = json.loads(m.group(1))
        
        # ─── Robust Extraction ───
        header = data.get("header", {})
        c4 = header.get("c4TabbedHeaderRenderer", {})
        ph = header.get("pageHeaderRenderer", {})

        title = ""
        subs  = 0
        thumb = ""
        
        # Title
        if c4.get("title"):
            title = c4["title"]
        elif ph.get("content", {}).get("pageHeaderViewModel", {}).get("title", {}).get("dynamicTextViewModel", {}).get("text", {}).get("content"):
            title = ph["content"]["pageHeaderViewModel"]["title"]["dynamicTextViewModel"]["text"]["content"]
        
        # Subscribers
        sub_text = ""
        if c4.get("subscriberCountText", {}).get("simpleText"):
            sub_text = c4["subscriberCountText"]["simpleText"]
        elif ph.get("content", {}).get("pageHeaderViewModel", {}).get("metadata", {}).get("contentMetadataViewModel", {}).get("metadataRows"):
            rows = ph["content"]["pageHeaderViewModel"]["metadata"]["contentMetadataViewModel"]["metadataRows"]
        # Subscribers, Views, Videos parsing
        subs = 0
        total_views = 0
        video_count = 0
        
        # Check all rows for metrics
        for r in rows:
            for p in r.get("metadataParts", []):
                txt = p.get("text", {}).get("content", "").lower().replace(",", "")
                # Parse Subscribers
                if "subscriber" in txt:
                    nums = re.findall(r"[\d.]+", txt)
                    if nums:
                        val = float(nums[0])
                        if "k" in txt: val *= 1000
                        elif "m" in txt: val *= 1000000
                        subs = int(val)
                # Parse Video Count
                elif "video" in txt:
                    nums = re.findall(r"[\d.]+", txt)
                    if nums:
                        video_count = int(float(nums[0]))
                # Parse View Count
                elif "view" in txt:
                    nums = re.findall(r"[\d.]+", txt)
                    if nums:
                        val = float(nums[0])
                        if "k" in txt: val *= 1000
                        elif "m" in txt: val *= 1000000
                        elif "b" in txt: val *= 1000000000
                        total_views = int(val)

        # Fallback for Total Views if still 0 (search entire data string for "views")
        if total_views == 0:
            json_str = str(data).lower()
            view_matches = re.findall(r"([\d,.]+)\s+views", json_str)
            if view_matches:
                v_txt = view_matches[0].replace(",", "")
                nums = re.findall(r"[\d.]+", v_txt)
                if nums: total_views = int(float(nums[0]))

        # Avatar / Thumbnail Extraction
        thumb = "https://www.gstatic.com/youtube/img/branding/youtubelogo/svg/youtubelogo.svg"
        logo_options = [
            c4.get("avatar", {}).get("thumbnails", []),
            ph.get("content", {}).get("pageHeaderViewModel", {}).get("image", {}).get("contentMetadataViewModel", {}).get("image", {}).get("sources", []),
            data.get("metadata", {}).get("channelMetadataRenderer", {}).get("avatar", {}).get("thumbnails", []),
            header.get("c4TabbedHeaderRenderer", {}).get("avatar", {}).get("thumbnails", [])
        ]
        
        for options in logo_options:
            if options and isinstance(options, list):
                thumb = options[-1]["url"]
                break
        
        # Ensure URL is complete and safe
        if thumb.startswith("//"): thumb = "https:" + thumb
        if "=" in thumb: thumb = thumb.split("=")[0] + "=s240-c-k-c0x00ffffff-no-rj" # High res

        # Channel ID
        cid = parsed
        if "metadata" in data:
            cid = data["metadata"].get("channelMetadataRenderer", {}).get("externalId", parsed)

        return {
            "id": cid,
            "name": title or parsed, # Renamed to 'name' for consistency if needed, but keeping 'title' for now
            "title": title or parsed,
            "description": "Fetched via Keyless Mode",
            "thumbnail": thumb,
            "country": "N/A",
            "published_at": datetime.now() - timedelta(days=730),
            "age_days": 730,
            "subscribers": subs,
            "hidden_subs": False,
            "total_views": total_views,
            "video_count": video_count,
            "is_keyless": True
        }
    except Exception as e:
        print(f"Fetch Error: {e}")
        return None
        return None

def _parse_published_time(text: str) -> datetime:
    """Convert strings like '1 month ago' to an approximate datetime."""
    now = datetime.now()
    text = text.lower()
    if "second" in text or "minute" in text or "hour" in text:
        return now
    
    nums = re.findall(r"\d+", text)
    if not nums:
        return now
    val = int(nums[0])
    
    if "day" in text:
        return now - timedelta(days=val)
    elif "week" in text:
        return now - timedelta(days=val * 7)
    elif "month" in text:
        return now - timedelta(days=val * 30)
    elif "year" in text:
        return now - timedelta(days=val * 365)
    return now

def _fetch_videos_via_scraping(channel_id_or_handle: str, max_results: int = 50) -> pd.DataFrame:
    """Fetch videos using scrapetube with proper date parsing."""
    try:
        videos = []
        parsed = _parse_channel_input(channel_id_or_handle)
        
        kwargs = {}
        if parsed.startswith("UC"):
            kwargs["channel_id"] = parsed
        else:
            kwargs["channel_url"] = f"https://www.youtube.com/@{parsed.lstrip('@')}"

        # Fetch videos explicitly
        gen = scrapetube.get_channel(**kwargs, content_type="videos")
        
        for i, vid in enumerate(gen):
            if i >= max_results:
                break
            
            vid_id = vid["videoId"]
            # Extract title safely
            title_runs = vid.get("title", {}).get("runs", [])
            title = title_runs[0].get("text", "Untitled") if title_runs else "Untitled"
            
            # IMPROVED VIEW PARSING
            view_texts = [
                vid.get("viewCountText", {}).get("simpleText", ""),
                vid.get("shortViewCountText", {}).get("simpleText", ""),
                vid.get("viewCountText", {}).get("runs", [{}])[0].get("text", "")
            ]
            
            views = 0
            for vt in view_texts:
                if vt:
                    nums = re.findall(r"[\d.]+", vt.lower().replace(",", ""))
                    if nums:
                        v = float(nums[0])
                        if "k" in vt.lower(): v *= 1000
                        elif "m" in vt.lower(): v *= 1000000
                        views = int(v)
                        if views > 0: break # Stop if found valid views

            # Date parsing "1 month ago"
            published_text = vid.get("publishedTimeText", {}).get("simpleText", "unknown")
            pub_date = _parse_published_time(published_text)

            videos.append({
                "video_id": vid_id,
                "title": title,
                "published_at": pub_date,
                "views": views,
                "likes": int(views * 0.05),
                "comments": int(views * 0.005),
                "publish_day": pub_date.strftime("%A"),
                "is_keyless": True
            })
        
        # If no regular videos, try shorts
        if not videos:
            gen_shorts = scrapetube.get_channel(**kwargs, content_type="shorts")
            for i, vid in enumerate(gen_shorts):
                if i >= max_results: break
                videos.append({
                    "video_id": vid["videoId"],
                    "title": "Short",
                    "published_at": datetime.now(),
                    "views": 0,
                    "likes": 0,
                    "comments": 0,
                    "publish_day": "Unknown",
                    "is_keyless": True
                })

        df = pd.DataFrame(videos)
        if not df.empty:
            df["engagement_score"] = df["views"] * 0.5 + df["likes"] * 2.0 + df["comments"] * 3.0
        return df
    except Exception as e:
        print(f"Video scraping failed: {e}")
        return pd.DataFrame()

# ─────────────────────────────────────────────
# Core fetch functions (cached)
# ─────────────────────────────────────────────

def fetch_channel_info(channel_input: str) -> dict | None:
    """Return channel metadata dict or None on failure using only scraping."""
    return _fetch_channel_via_scraping(channel_input)

def fetch_recent_videos(channel_id_or_handle: str, max_results: int = 100) -> pd.DataFrame:
    """Fetch recent videos using scrapetube."""
    return _fetch_videos_via_scraping(channel_id_or_handle, max_results)

def build_growth_history(channel_info: dict, videos_df: pd.DataFrame) -> pd.DataFrame:
    """
    Approximate subscriber growth history. 
    Without API, we use a simulation based on video upload timeline 
    and current total subscribers.
    """
    if videos_df.empty:
        # Create a dummy growth table if no videos
        dates = pd.date_range(end=datetime.now(), periods=52, freq="W")
        subs = np.linspace(0, channel_info["subscribers"], 52).astype(int)
        df = pd.DataFrame({"date": dates, "est_subs": subs})
        df["growth_rate_weekly"] = df["est_subs"].pct_change() * 100
        df["growth_rate_monthly"] = df["est_subs"].pct_change(4) * 100
        return df

    total_subs = channel_info["subscribers"]
    
    # Sort oldest first
    df = videos_df.sort_values("published_at").reset_index(drop=True)
    df["cum_views"] = df["views"].cumsum()
    max_views = df["cum_views"].max()

    if max_views == 0:
        df["est_subs"] = np.linspace(0, total_subs, len(df)).astype(int)
    else:
        # Map cumulative views to total subscribers
        df["est_subs"] = ( (df["cum_views"] / max_views) * total_subs ).astype(int)

    # Convert to weekly format for forecasting
    df["date"] = pd.to_datetime(df["published_at"]).dt.tz_localize(None)
    history = df[["date", "est_subs"]].copy()
    
    # Resample to weekly
    history = history.set_index("date").resample("W").max().ffill().reset_index()
    history["growth_rate_weekly"] = history["est_subs"].pct_change() * 100
    history["growth_rate_monthly"] = history["est_subs"].pct_change(4) * 100
    
    return history

def build_history_if_possible(info, vids):
    return build_growth_history(info, vids)


def fetch_comments(video_id: str, max_results: int = 100) -> list:
    """Fetch comments for a video using API Key or provide dummy data for simulation."""
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        return [
            "This was so helpful, thanks!", "How do I start building this?", 
            "Can you do a tutorial on React next?", "I'm stuck at the API step, please help.",
            "Great video as always!", "Best channel for tech tips.", 
            "Why is the code not working for me?", "What mic are you using?"
        ] * 10 # Provide enough mock text for AI analysis
    
    try:
        youtube = _build_service(api_key)
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=max_results,
            textFormat="plainText"
        )
        response = request.execute()
        
        comments = []
        for item in response.get("items", []):
            comment = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            comments.append(comment)
        return comments
    except Exception as e:
        return [f"Error fetching comments: {str(e)}"]


# ─────────────────────────────────────────────
# Demo / Mock data (no API key required)
# ─────────────────────────────────────────────

def get_demo_channel_info() -> dict:
    published = datetime(2019, 6, 1, tzinfo=None)
    age_days = (datetime.now() - published).days
    return {
        "id": "DEMO_CHANNEL",
        "title": "Demo Tech Channel 🚀",
        "description": "A demo channel for showcase purposes.",
        "thumbnail": "https://via.placeholder.com/88",
        "country": "US",
        "published_at": published,
        "age_days": age_days,
        "subscribers": 124_500,
        "hidden_subs": False,
        "total_views": 8_430_000,
        "video_count": 187,
        "uploads_playlist": "DEMO",
    }


def get_demo_videos_df() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    n = 40
    base = datetime(2024, 1, 1)
    dates = [base + timedelta(days=int(i * 7 + rng.integers(-3, 3))) for i in range(n)]
    titles = [
        "Why Python is Still King in 2024", "10x Your Code Speed", "Machine Learning Crash Course",
        "Build a REST API in 10 Min", "Docker for Beginners", "React vs Vue 2024",
        "GPT-4 Integration Guide", "CI/CD Pipeline Setup", "Kubernetes Explained",
        "Streamlit Dashboard Tutorial", "FastAPI Deep Dive", "PostgreSQL vs MongoDB",
        "WebSockets in Python", "GraphQL Basics", "Rust for Python Devs",
        "Async Python Tutorial", "Cloud Cost Optimization", "GitHub Actions 101",
        "TensorFlow 2.0 Guide", "Pandas Performance Tips", "Redis Caching",
        "Microservices Architecture", "Linux Command Mastery", "TypeScript 5 Guide",
        "Next.js 14 Features", "Svelte vs React", "AWS Lambda Tutorial",
        "Terraform Basics", "Ansible Automation", "Vim Tricks",
        "Clean Code Principles", "Design Patterns in Python", "SOLID Principles",
        "Test Driven Development", "Data Engineering Basics", "Spark Tutorial",
        "Airflow Workflows", "dbt for Analytics", "Vector Databases",
        "LangChain Crash Course",
    ]
    views   = rng.integers(5_000, 400_000, n)
    likes   = (views * rng.uniform(0.02, 0.08, n)).astype(int)
    comments= (views * rng.uniform(0.001, 0.01, n)).astype(int)

    df = pd.DataFrame({
        "video_id": [f"vid_{i:03d}" for i in range(n)],
        "title": titles[:n],
        "published_at": pd.to_datetime(dates),
        "views": views,
        "likes": likes,
        "comments": comments,
    })
    df["publish_day"] = df["published_at"].dt.day_name()
    df["engagement_score"] = df["views"] * 0.5 + df["likes"] * 2.0 + df["comments"] * 3.0
    return df.sort_values("published_at", ascending=False).reset_index(drop=True)


def get_demo_growth_history() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    dates = pd.date_range("2019-06-01", periods=260, freq="W")
    base   = np.linspace(0, 100_000, 160)
    accel  = np.linspace(100_000, 124_500, 100)
    subs   = np.concatenate([base, accel])
    noise  = rng.normal(0, 800, 260)
    subs   = np.clip(np.cumsum(np.diff(np.concatenate([[0], subs])) + noise), 0, 124_500)
    df = pd.DataFrame({"date": dates, "est_subs": subs.astype(int)})
    df["growth_rate_weekly"]  = df["est_subs"].pct_change() * 100
    df["growth_rate_monthly"] = df["est_subs"].pct_change(4) * 100
    return df
