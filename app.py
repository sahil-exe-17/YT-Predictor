"""
app.py — YouTube Channel Analytics & Subscriber Predictor
Simplified, high-contrast UI with no sidebar.
"""

import os
import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from dotenv import load_dotenv
from datetime import datetime

# Local modules
import fetcher
import predictor
import insights
import ai_features

load_dotenv()

# ─────────────────────────────────────────────
# Page config & global CSS (Metric Pure Design)
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="YT Predictor — Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS for high-contrast professional look
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Manrope:wght@700;800&display=swap');

/* global reset */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #f7f9fb !important;
    color: #191c1e;
    font-family: 'Inter', sans-serif;
}

[data-testid="stHeader"] { background: rgba(0,0,0,0); }
[data-testid="stSidebar"] { display: none; }

/* Main title */
.main-title {
    font-family: 'Manrope', sans-serif;
    font-size: 2.5rem;
    font-weight: 800;
    color: #00193c;
    margin-bottom: 0.2rem;
    text-align: center;
}
.sub-title {
    color: #43474f;
    font-size: 1rem;
    text-align: center;
    margin-bottom: 2rem;
}

/* Control Panel Card */
.control-panel {
    background: #ffffff;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    margin-bottom: 24px;
    border: 1px solid #e0e3e5;
}

/* Metric cards (Clean/High-Contrast) */
.metric-card {
    background: #ffffff;
    border: 1px solid #e0e3e5;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
}
.metric-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: #43474f;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 8px;
}
.metric-value {
    font-family: 'Manrope', sans-serif;
    font-size: 2.2rem;
    font-weight: 800;
    color: #00193c;
}
.metric-sub {
    font-size: 0.8rem;
    color: #64748b;
    margin-top: 4px;
}

/* Section headers */
.section-header {
    font-family: 'Manrope', sans-serif;
    font-size: 1.25rem;
    font-weight: 700;
    color: #00193c;
    margin: 1.5rem 0 0.75rem;
    border-bottom: 2px solid #00193c;
    width: fit-content;
    padding-bottom: 4px;
}

/* Multi-color insights */
.insight-box {
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
    font-size: 0.95rem;
}
.insight-good { background: #ecfdf5; border-left: 5px solid #10b981; color: #064e3b; }
.insight-warn { background: #fff7ed; border-left: 5px solid #f97316; color: #7c2d12; }
.insight-info { background: #eff6ff; border-left: 5px solid #3b82f6; color: #1e3a8a; }

/* Tabs */
[data-testid="stTabs"] [role="tablist"] {
    gap: 8px;
}
[data-testid="stTabs"] button[role="tab"] {
    background-color: #eceef0;
    border-radius: 8px 8px 0 0;
    color: #43474f;
    font-weight: 600;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    background-color: #00193c !important;
    color: white !important;
}

/* Channel Banner */
.channel-banner {
    display: flex;
    align-items: center;
    gap: 16px;
    background: #ffffff;
    border: 1px solid #e0e3e5;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 20px;
}
.channel-banner img {
    width: 60px;
    height: 60px;
    border-radius: 50%;
    object-fit: cover;
}
.channel-name { font-size: 1.3rem; font-weight: 800; color: #00193c; }

/* Buttons */
.stButton > button {
    background-color: #00193c;
    color: white;
    border-radius: 6px;
}
.stButton > button:hover {
    background-color: #002d62;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Utility: format large numbers
# ─────────────────────────────────────────────
def fmt(n: int | float) -> str:
    n = int(n)
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


# ─────────────────────────────────────────────
# UI Constants (Derived from Stitch Metric Pure)
# ─────────────────────────────────────────────
PRIMARY_BLUE  = "#00193c"
SURFACE_LIGHT = "#f7f9fb"
SURFACE_WHITE = "#ffffff"
TEXT_DARK = "#191c1e"
TEXT_MUTED = "#43474f"


# ─────────────────────────────────────────────
# Plotly theme helper (Light Mode)
# ─────────────────────────────────────────────
PLOTLY_LAYOUT = dict(
    paper_bgcolor="#ffffff",
    plot_bgcolor="#ffffff",
    font=dict(color="#191c1e", family="Inter, sans-serif"),
    xaxis=dict(gridcolor="#eceef0", zerolinecolor="#eceef0", tickfont=dict(size=10)),
    yaxis=dict(gridcolor="#eceef0", zerolinecolor="#eceef0", tickfont=dict(size=10)),
    legend=dict(bgcolor="#ffffff", bordercolor="#e0e3e5", borderwidth=1),
    margin=dict(l=40, r=40, t=40, b=40),
)


# ─────────────────────────────────────────────
# Session-state initialisation
# ─────────────────────────────────────────────
for key in ["channel_info", "videos_df", "history_df", "forecast", "milestones",
            "comp_info", "comp_videos", "comp_history", "loaded",
            "ai_title_opt", "ai_growth_plan", "ai_gap_analysis", "ai_faqs", "ai_weekly_sum", "ai_viral_score"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ─────────────────────────────────────────────
# Header & Dashboard Control Panel (Moved from Sidebar)
# ─────────────────────────────────────────────
st.markdown('<div class="main-title">📈 YT Predictor</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Advanced YouTube Analytics & Growth Prediction Engine</div>', unsafe_allow_html=True)

# Control Panel with refined design

with st.container():
    st.markdown('<div class="control-panel">', unsafe_allow_html=True)
    
    col_a, col_b, col_c = st.columns([2, 1, 1])
    
    with col_a:
        channel_input = st.text_input(
            "Channel Link or @Handle",
            placeholder="e.g. @MrBeast or https://youtube.com/user/...",
            key="ch_input"
        )
        demo_mode = st.toggle("🎭 Demo Mode (Simulate Active Data)", value=False)
        
    with col_b:
        goal_subs = st.number_input(
            "Subscriber Target",
            min_value=1000, value=250000, step=10000,
            key="goal_input"
        )
        
    with col_c:
        competitor_input = st.text_input(
            "Compare with Channel",
            placeholder="@Competitor",
            key="comp_input"
        )
        
    btn_col1, btn_col2, _ = st.columns([1, 1, 2])
    with btn_col1:
        fetch_btn = st.button("🚀 Run Analysis", use_container_width=True)
    with btn_col2:
        compare_btn = st.button("⚔️ View Battle", use_container_width=True)
        
    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Logic: Data Load
# ─────────────────────────────────────────────
if demo_mode and not st.session_state.loaded:
    with st.spinner("Initializing system..."):
        st.session_state.channel_info = fetcher.get_demo_channel_info()
        st.session_state.videos_df    = fetcher.get_demo_videos_df()
        st.session_state.history_df   = fetcher.get_demo_growth_history()
        st.session_state.forecast     = predictor.prophet_forecast(st.session_state.history_df)
        st.session_state.milestones   = predictor.get_milestone_predictions(st.session_state.forecast)
        st.session_state.loaded       = True
        st.rerun()

if fetch_btn and channel_input:
    with st.spinner("Scanning Channel..."):
        ch = fetcher.fetch_channel_info(channel_input)
    if ch is None:
        st.error("❌ Link invalid or channel unavailable. Try another handle.")
    else:
        st.session_state.channel_info = ch
        with st.spinner("Downloading Analytics..."):
            vids = fetcher.fetch_recent_videos(ch["id"])
            st.session_state.videos_df = vids
            hist = fetcher.build_growth_history(ch, vids)
            st.session_state.history_df = hist
        with st.spinner("Calculating Predictions..."):
            fc = predictor.prophet_forecast(hist, days_ahead=90)
            ms = predictor.get_milestone_predictions(fc)
            st.session_state.forecast   = fc
            st.session_state.milestones = ms
            st.session_state.loaded     = True

if compare_btn and competitor_input:
    with st.spinner("Analyzing Rival..."):
        comp = fetcher.fetch_channel_info(competitor_input)
        if comp:
            comp_vids = fetcher.fetch_recent_videos(comp["id"])
            comp_hist = fetcher.build_growth_history(comp, comp_vids)
            st.session_state.comp_info    = comp
            st.session_state.comp_videos  = comp_vids
            st.session_state.comp_history = comp_hist
        else:
            st.warning("Competitor not found.")

# ─────────────────────────────────────────────
# Dashboard View
# ─────────────────────────────────────────────
if not st.session_state.loaded:
    st.info("👋 Welcome! Paste a YouTube channel link above to begin your analysis.")
    st.stop()

# Channel Profile Header
ch = st.session_state.channel_info
with st.container():
    c1, c2 = st.columns([1, 6])
    with c1:
        st.image(ch["thumbnail"], width=80)
    with c2:
        st.markdown(f'<div class="channel-name">{ch["title"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="color:#64748b; font-size:0.9rem;">ID: {ch["id"]} • Analysis Mode: {"Demo" if demo_mode else "Keyless Live"}</div>', unsafe_allow_html=True)
st.markdown('<div style="height: 20px;"></div>', unsafe_allow_html=True)

# Top Metrics
m1, m2, m3, m4 = st.columns(4)
metrics = [
    ("Subscribers", fmt(ch["subscribers"]), "Current total"),
    ("Lifetime Views", fmt(ch["total_views"]), "All time"),
    ("Video Count", f"{ch['video_count']:,}", "Total uploads"),
    ("Growth Status", "Stable", "Last 30 days")
]
for col, (lbl, val, sub) in zip([m1, m2, m3, m4], metrics):
    with col:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">{lbl}</div>
          <div class="metric-value">{val}</div>
          <div class="metric-sub">{sub}</div>
        </div>""", unsafe_allow_html=True)

# Tabs
tab_overview, tab_forecast, tab_content, tab_strategy, tab_rival, tab_title_opt, tab_coach, tab_gap, tab_faq, tab_weekly, tab_viral = st.tabs([
    "📈 Growth history", "🔮 Future Forecast", "🎬 Video Analytics", "💡 Strategy", "⚔️ Rival Battle",
    "✍️ Title Optimizer", "🧠 Growth Coach", "🔬 Gap Analysis", "💬 FAQ Extractor", "📅 Weekly Summary", "🔥 Viral Scorer"
])

with tab_overview:
    st.markdown('<div class="section-header">Subscriber Progression</div>', unsafe_allow_html=True)
    hist_df = st.session_state.history_df
    if not hist_df.empty:
        fig = px.area(hist_df, x="date", y="est_subs", 
                      labels={"est_subs":"Subscribers","date":"Date"},
                      template="plotly_white")
        fig.update_traces(line_color=PRIMARY_BLUE, fillcolor="rgba(0,25,60,0.1)")
        fig.update_layout(**PLOTLY_LAYOUT, height=400)
        st.plotly_chart(fig, use_container_width=True)

with tab_forecast:
    st.markdown('<div class="section-header">90-Day Prediction Model</div>', unsafe_allow_html=True)
    fc = st.session_state.forecast
    ms = st.session_state.milestones
    if fc:
        full_df = fc["full_df"]
        fig_fc = go.Figure()
        # Conf
        fig_fc.add_trace(go.Scatter(
            x=pd.concat([full_df["date"], full_df["date"][::-1]]),
            y=pd.concat([full_df["upper"], full_df["lower"][::-1]]),
            fill="toself", fillcolor="rgba(0,0,0,0.05)", line_color="rgba(0,0,0,0)", name="Confidence"
        ))
        # Forecast
        fig_fc.add_trace(go.Scatter(
            x=full_df["date"], y=full_df["predicted"], 
            line=dict(color=PRIMARY_BLUE, width=3, dash="dot"), name="Forecast"
        ))
        fig_fc.update_layout(**PLOTLY_LAYOUT, height=450)
        st.plotly_chart(fig_fc, use_container_width=True)

        # Milestone row
        mc1, mc2, mc3 = st.columns(3)
        for col, d in zip([mc1, mc2, mc3], [30, 60, 90]):
            m = ms.get(d)
            if m:
                with col:
                    st.markdown(f'<div class="metric-card"><div class="metric-label">Target {d} Days</div><div class="metric-value">{fmt(m["predicted"])}</div></div>', unsafe_allow_html=True)

with tab_content:
    st.markdown('<div class="section-header">Recent Performance</div>', unsafe_allow_html=True)
    vids = st.session_state.videos_df
    if vids is not None:
        st.dataframe(vids[["title", "views", "likes", "comments", "engagement_score"]].head(10), use_container_width=True)

with tab_strategy:
    st.markdown('<div class="section-header">JARVIS-X Strategic Advisory</div>', unsafe_allow_html=True)
    vids = st.session_state.videos_df
    hist = st.session_state.history_df
    advice = insights.generate_strategic_advisory(vids, hist)
    for adv in advice:
        cls = f"insight-{adv['level']}"
        st.markdown(f'<div class="insight-box {cls}">{adv["text"]}</div>', unsafe_allow_html=True)

with tab_rival:
    st.markdown('<div class="section-header">The Battleground</div>', unsafe_allow_html=True)
    comp_info = st.session_state.comp_info
    if comp_info:
        comp_df = insights.compare_channels(ch, comp_info)
        st.dataframe(comp_df, use_container_width=True)
    else:
        st.info("Enter a rival channel URL in the Control Panel above to start comparison.")

with tab_title_opt:
    st.markdown('<div class="section-header">AI Title Optimizer</div>', unsafe_allow_html=True)
    curr_title = st.text_input("Enter your current video title", placeholder="e.g. How to grow on YouTube")
    if st.button("Optimize Title"):
        with st.spinner("Analyzing title potential..."):
            res = ai_features.optimize_title(curr_title)
            st.session_state.ai_title_opt = res
    if st.session_state.ai_title_opt:
        st.markdown(st.session_state.ai_title_opt)

with tab_coach:
    st.markdown('<div class="section-header">AI Growth Coach</div>', unsafe_allow_html=True)
    if st.button("Get My Growth Plan"):
        with st.spinner("Analyzing your channel..."):
            stats = {
                "subs": fmt(ch["subscribers"]),
                "views": fmt(ch["total_views"]),
                "video_count": ch["video_count"],
                "channel_name": ch["title"],
                "growth": st.session_state.history_df["growth_rate_monthly"].iloc[-1] if not st.session_state.history_df.empty else "Unknown",
                "avg_views": int(ch["total_views"] / ch["video_count"]) if ch["video_count"] > 0 else 0,
                "uploads_per_week": 1, 
                "top_video_title": st.session_state.videos_df["title"].iloc[0] if not st.session_state.videos_df.empty else "N/A"
            }
            res = ai_features.get_growth_plan(stats)
            st.session_state.ai_growth_plan = res
    if st.session_state.ai_growth_plan:
        st.markdown(st.session_state.ai_growth_plan)

with tab_gap:
    st.markdown('<div class="section-header">Competitor Gap Analyzer</div>', unsafe_allow_html=True)
    if st.session_state.comp_info:
        if st.button("Analyze Gap"):
            with st.spinner("Comparing content strategies..."):
                my_titles = st.session_state.videos_df["title"].tolist()
                comp_titles = st.session_state.comp_videos["title"].tolist()
                names = {"me": ch["title"], "comp": st.session_state.comp_info["title"]}
                res = ai_features.analyze_competitor_gap(my_titles, comp_titles, names)
                st.session_state.ai_gap_analysis = res
        if st.session_state.ai_gap_analysis:
            st.markdown(st.session_state.ai_gap_analysis)
    else:
        st.warning("Please search for a regular channel AND a competitor first.")

with tab_faq:
    st.markdown('<div class="section-header">FAQ Extractor</div>', unsafe_allow_html=True)
    vids_list = st.session_state.videos_df
    if vids_list is not None and not vids_list.empty:
        selected_vid_title = st.selectbox("Select a video", vids_list["title"].unique())
        selected_vid_id = vids_list[vids_list["title"] == selected_vid_title]["video_id"].iloc[0]
        if st.button("Extract FAQs from Comments"):
            with st.spinner("Fetching comments..."):
                comments = fetcher.fetch_comments(selected_vid_id)
                with st.spinner("Extracting insights..."):
                    res = ai_features.extract_faqs_from_comments(comments, selected_vid_title)
                    st.session_state.ai_faqs = res
        if st.session_state.ai_faqs:
            st.markdown(st.session_state.ai_faqs)
    else:
        st.info("No videos loaded to analyze.")

with tab_weekly:
    st.markdown('<div class="section-header">Weekly AI Summary</div>', unsafe_allow_html=True)
    if st.button("Generate This Week's Summary"):
        with st.spinner("Analyzing weekly performance..."):
            hist = st.session_state.history_df
            vids = st.session_state.videos_df
            # Use video-sum as floor if channel total_views scraping returned 0
            video_views_sum = int(vids["views"].sum()) if not vids.empty else 0
            display_views = ch["total_views"] if ch["total_views"] > 0 else video_views_sum
            weekly_views = int(vids["views"].head(7).sum()) if not vids.empty else 0

            weekly_stats = {
                "channel_name": ch["title"],
                "weekly_subs": int(hist["est_subs"].iloc[-1] - hist["est_subs"].iloc[-2]) if len(hist) > 1 else 0,
                "weekly_views": weekly_views,
                "weekly_uploads": len(vids[vids["published_at"] > (datetime.now() - pd.Timedelta(days=7))]) if not vids.empty else 0,
                "best_video": vids.iloc[0]["title"] if not vids.empty else "N/A",
                "worst_video": vids.iloc[-1]["title"] if not vids.empty else "N/A",
                "growth": round(hist["growth_rate_weekly"].iloc[-1], 2) if len(hist) > 0 else 0,
                "views": fmt(display_views),
                "title": vids.iloc[0]["title"] if not vids.empty else "Topic"
            }
            res = ai_features.generate_weekly_summary(weekly_stats)
            st.session_state.ai_weekly_sum = res
    if st.session_state.ai_weekly_sum:
        st.markdown(st.session_state.ai_weekly_sum)

with tab_viral:
    st.markdown('<div class="section-header">Viral Potential Scorer</div>', unsafe_allow_html=True)
    idea = st.text_input("Enter your video idea or title", placeholder="e.g. I spent 100 days in a VR world")
    niche = st.text_input("Your niche/topic", placeholder="e.g. Gaming, Tech")
    if st.button("Score My Idea"):
        with st.spinner("Predicting virality..."):
            res = ai_features.score_viral_potential(idea, niche)
            st.session_state.ai_viral_score = res
    if st.session_state.ai_viral_score:
        st.markdown(st.session_state.ai_viral_score)
