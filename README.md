# 📈 YT Predictor — YouTube Analytics & Growth Assistant

A **keyless** YouTube analytics dashboard built with Python & Streamlit. No YouTube API key required for core features!

## 🚀 Features
- 📊 **Full Channel Analytics** — Subscribers, views, video count scraped directly from YouTube
- 📈 **Growth History & Forecasting** — 90-day subscriber predictions powered by Facebook Prophet
- ⚔️ **Rival Battle** — Side-by-side competitor comparison
- 🤖 **6 Expert AI Modules** (Logic-Powered & Keyless):
  - Title Optimizer
  - Growth Coach
  - Competitor Gap Analyzer
  - FAQ Intelligence
  - Weekly Briefing
  - Predictive Viral Scorer
- 🎭 **Zero-Config Deployment** — Works out-of-the-box without any account or API keys!

## 🛠️ Local Setup

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/yt-predictor.git
cd yt-predictor
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment variables
```bash
cp .env.example .env
```
Edit `.env` and add your keys:
```
GEMINI_API_KEY=your_gemini_api_key_here   # Optional — for live AI features
YOUTUBE_API_KEY=your_yt_api_key_here      # Optional — for comment analysis only
```
> 💡 Get a free Gemini key at [aistudio.google.com](https://aistudio.google.com/)

### 4. Run the app
```bash
streamlit run app.py
```
Then open [http://localhost:8501](http://localhost:8501) in your browser.

## ☁️ Deployment

### Option 1: Streamlit Community Cloud (Easiest)
1. Push your code to GitHub.
2. Visit [share.streamlit.io](https://share.streamlit.io).
3. Connect your repo and set `app.py` as the main file.
4. **Important**: Go to **Advanced Settings** → **Secrets** and paste:
   ```toml
   GEMINI_API_KEY = "your_key"
   YOUTUBE_API_KEY = "your_key"
   ```

### Option 2: Render.com
This repo includes a `render.yaml` for one-click deployment.
1. Connect your GitHub to Render.
2. Select **"Blueprint"** or simply "Web Service".
3. Add your environment variables in the Render Dashboard.

## 📦 Tech Stack
| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit |
| Scraping | scrapetube, requests |
| AI | Google Gemini 1.5 Pro |
| Forecasting | Facebook Prophet |
| Data | Pandas, NumPy |
| Charts | Plotly |

## 📁 Project Structure
```
yt-predictor/
├── app.py           # Main Streamlit UI
├── fetcher.py       # YouTube data scraping engine
├── predictor.py     # Prophet forecasting model
├── insights.py      # Analytics calculations
├── ai_features.py   # Gemini AI integrations
├── requirements.txt
├── .env.example
└── README.md
```

## ⚠️ Notes
- This tool uses **web scraping** (no official API required for core features)
- YouTube's page structure can change; if data shows as 0, re-run the analysis
- All AI features gracefully degrade to simulated results if no API key is provided
