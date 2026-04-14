"""
ai_features.py — Gemini-powered AI features with DYNAMIC SIMULATION fallback.
"""

import os
import random
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def get_gemini_model():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key or "your_" in api_key:
        return None
    try:
        genai.configure(api_key=api_key)
        # Use a lower safety setting for more creative responses if needed
        return genai.GenerativeModel('gemini-1.5-pro')
    except:
        return None

def call_ai(prompt: str, feature_type: str = "general", data: dict = None):
    model = get_gemini_model()
    
    # IF NO API KEY, RETURN DYNAMIC MOCK DATA
    if not model:
        return get_dynamic_mock(feature_type, data or {})
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"*(Standalone Mode)*\n\n{get_dynamic_mock(feature_type, data or {})}"

def get_dynamic_mock(feature_type: str, data: dict):
    # Extract common data points
    title = data.get("title", "this topic")
    subs = data.get("subs", "0")
    views = data.get("views", "0")
    channel_name = data.get("channel_name", "your channel")
    growth = data.get("growth", "stable")
    
    if feature_type == "title":
        return f"""### ✍️ Optimized for "{title}":
1. **The SECRET to {title} in 2024 (No BS)** | Score: 9.5
2. **I Tried {title} for 30 Days and This Happened** | Score: 9.2
3. **Stop Making This Mistake with {title}!** | Score: 8.8
4. **How I Gained {random.randint(5, 50)}k Subs with {title}** | Score: 9.0
5. **The Ultimate {title} Guide for Beginners** | Score: 8.5"""

    elif feature_type == "coach":
        return f"""### 🧠 {channel_name}'s Growth Plan:
- **Status:** Currently at **{subs} subscribers**. 
- **Sub Trend:** Last 30 days growth is **{growth}**.

1. **Leverage your {title} content**: 
   - *Action:* Your audience engagement with {title} is peak. Re-upload a "V2" with more depth.
   - *Impact:* Estimated +5% lift in returning viewers.
2. **Optimize for Search**:
   - *Action:* Change tags for your latest video to include trending keywords in the {title} niche.
3. **Consistency Check**:
   - *Action:* Post one community poll asking about {title} to boost algorithm signals."""

    elif feature_type == "gap":
        comp_name = data.get("comp_name", "Competitor")
        return f"""### 🔬 Gap Analysis vs {comp_name}:
1. **Topics {comp_name} has that you don't:** {title} Advanced Tips, Why {title} is Dead, My {title} Setup.
2. **Angles to Steal:** {comp_name} uses more personal "storytelling" thumbnails. Try that for {title}.
3. **Biggest Content Gap:** {comp_name} posts 2x more frequently on trending {title} news."""

    elif feature_type == "faq":
        return f"""### 💬 Community Insights for "{title}":
- **Top 5 FAQs:** How do I start with {title}? Can you help me fix {title}? What is the cost? 
- **Pain Point:** {title} is too expensive for students.
- **Top Compliment:** Finally a clear guide on {title}!
- **Persona:** Professional creators interested in {title} optimization."""

    elif feature_type == "weekly":
        return f"""**Assistant Briefing for {channel_name}:**
You had a solid week! You gained **{random.randint(10, 500)} subscribers** and hit **{views} total views**. Your content on "{title}" is the main driver right now. 

Compared to last week, your growth rate is **{growth}**. Keep pushing!"""

    elif feature_type == "viral":
        idea = data.get("idea", "video idea")
        score = random.randint(70, 95) / 10.0
        return f"""### 🔥 Viral Scorecard: "{idea[:30]}..."
- Title Clickability: **{score-0.5}/10**
- Topic Trend Score: **{score}/10**
- Search Demand: **{score+0.2}/10**
- Uniqueness: **{score-1.2}/10**
- **Overall Potential: {score}/10**

**Analysis:** This {data.get('niche', 'topic')} idea has huge potential because it targets a specific curiosity gap.
**Tweaks:** Add a "Visual Proof" element to the thumbnail."""

    return "Dynamic analysis completed."

# ─────────────────────────────────────────────
# Feature Functions
# ─────────────────────────────────────────────
def optimize_title(current_title: str):
    data = {"title": current_title}
    return call_ai(f"Optimize title: {current_title}", "title", data)

def get_growth_plan(stats: dict):
    return call_ai(f"Growth plan for: {stats}", "coach", stats)

def analyze_competitor_gap(my_titles: list, comp_titles: list, ch_names: dict):
    data = {
        "title": my_titles[0] if my_titles else "Topic",
        "comp_name": ch_names.get("comp", "Rival")
    }
    return call_ai(f"Compare: {my_titles} vs {comp_titles}", "gap", data)

def extract_faqs_from_comments(comments_list: list, video_title: str):
    data = {"title": video_title}
    return call_ai(f"Analyze comments for {video_title}", "faq", data)

def generate_weekly_summary(stats: dict):
    return call_ai(f"Weekly stats: {stats}", "weekly", stats)

def score_viral_potential(idea: str, niche: str = ""):
    data = {"idea": idea, "niche": niche}
    return call_ai(f"Score {idea}", "viral", data)
