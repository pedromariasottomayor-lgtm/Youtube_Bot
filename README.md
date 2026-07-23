# 🤖 YouTube Automation Bot

> **Automatically generates and uploads YouTube Shorts every day — 100% free, zero manual work.**

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Cost](https://img.shields.io/badge/Cost-$0%2Fmonth-brightgreen)](README.md)
[![YouTube API](https://img.shields.io/badge/YouTube-Data%20API%20v3-red?logo=youtube)](https://developers.google.com/youtube/v3)

---

## 📌 What This Bot Does

Every time it runs, the bot automatically:

1. **Picks a topic** from your list (cycles through them daily)
2. **Writes a script** using Google Gemini AI (free API)
3. **Generates a voiceover** using Microsoft Edge TTS (free, sounds human)
4. **Creates AI cartoon illustrations** using Pollinations.ai (free, no key)
5. **Assembles a vertical 1080×1920 Shorts video** with slides + audio
6. **Uploads to your YouTube channel** with title, description, and tags
7. **Repeats automatically** every day via GitHub Actions or Task Scheduler

**Total cost: $0.00/month**

---

## 🛠️ Tech Stack

| Step | Tool | Cost |
|------|------|------|
| Script generation | Google Gemini API (free tier) | FREE |
| Voiceover | Microsoft Edge TTS | FREE |
| AI illustrations | Pollinations.ai | FREE |
| Video assembly | MoviePy + FFmpeg | FREE |
| Image processing | Pillow (PIL) | FREE |
| YouTube upload | YouTube Data API v3 | FREE |
| Scheduling | GitHub Actions | FREE |

---

## 📁 Project Structure

```
youtube_bot/
├── main.py                        # Main pipeline — run this
├── requirements.txt               # All Python dependencies
├── run_bot.bat                    # Windows Task Scheduler launcher
├── run_bot.sh                     # Linux/Mac cron launcher
├── .github/
│   └── workflows/
│       └── auto_upload.yml        # GitHub Actions daily schedule
├── scripts/
│   ├── __init__.py
│   ├── generate_script.py         # Step 1: AI script via Gemini
│   ├── generate_voice.py          # Step 2: Voiceover via Edge TTS
│   ├── generate_video.py          # Step 3: Video via MoviePy + Pillow
│   └── upload_youtube.py          # Step 4: Upload via YouTube API
└── output/                        # Generated files (gitignored)
    └── .gitkeep
```

> ⚠️ `client_secrets.json` and `youtube_token.pickle` are **gitignored** — never commit them.

---

## ⚡ Quick Start (5 Steps)

### Step 1 — Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/youtube-bot.git
cd youtube-bot
```

### Step 2 — Set up Python environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3 — Get your free Gemini API key

1. Go to **https://aistudio.google.com/app/apikey**
2. Sign in with any Google account
3. Click **"Create API Key"** → copy the key
4. Open `scripts/generate_script.py` → replace `YOUR_GEMINI_API_KEY_HERE` with your key

> Free limit: **1,500 requests/day** — far more than needed for 1 video/day.

### Step 4 — Set up YouTube API

> Follow these steps carefully — this is the only complex part.

#### 4a. Create Google Cloud Project
1. Go to **https://console.cloud.google.com**
2. Click **"Select a project"** → **"New Project"**
3. Name: `YouTube Bot` → **Create**

#### 4b. Enable YouTube Data API
1. **APIs & Services** → **Library**
2. Search: `YouTube Data API v3` → Click → **Enable**

#### 4c. Configure OAuth Consent Screen
1. **APIs & Services** → **OAuth consent screen**
2. Click **"Get started"**
3. Fill in App name: `YouTube Bot`, your email
4. User type: **External**
5. Add your Gmail as a **test user**
6. Click through and save

#### 4d. Create Credentials
1. **APIs & Services** → **Credentials** → **+ Create Credentials** → **OAuth Client ID**
2. Application type: **Desktop app**
3. Name: `YouTube Bot` → **Create**
4. Click **Download JSON**
5. Rename the file to: `client_secrets.json`
6. Place it in the **project root folder** (same level as `main.py`)

#### 4e. First login (one time only)
```bash
python main.py --dry-run
```
A browser window opens → log in with your YouTube account → click **Allow** → done forever. The bot saves a token so you never need to log in again.

### Step 5 — Customize and run

Open `main.py` and edit the `TOPICS` list with your niche:

```python
TOPICS = [
    "5 Amazing Facts About Space",
    "How Artificial Intelligence Works",
    "Interesting Facts About the Ocean",
    # Add your own topics here...
]
```

Then run:

```bash
python main.py
```

---

## 🧪 Test Without API Keys

Test the full pipeline without needing any API keys:

```bash
# Use offline script (no Gemini needed)
python main.py --offline

# Skip YouTube upload (just generate the video)
python main.py --offline --dry-run

# Use a specific topic
python main.py --topic "How gravity works" --dry-run

# Test individual scripts
python scripts/generate_script.py   # Test script generator
python scripts/generate_voice.py    # Creates output/test_voice.mp3
python scripts/generate_video.py    # Creates output/slides/test_slide.png
```

---

## ⏰ Scheduling (Automatic Daily Uploads)

### Option A: GitHub Actions (Recommended — runs in cloud)

Runs every day at 10:00 AM UTC even when your PC is off.

1. Push this repo to GitHub (public or private)
2. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
3. Add these secrets:
   - `GEMINI_API_KEY` → your Gemini key
   - `YOUTUBE_TOKEN_B64` → your YouTube token (see below)

**How to get `YOUTUBE_TOKEN_B64`:**

After running the bot locally once (to create `youtube_token.pickle`):

```bash
# Windows PowerShell:
[Convert]::ToBase64String([IO.File]::ReadAllBytes("youtube_token.pickle"))

# Mac/Linux:
base64 -w 0 youtube_token.pickle
```

Copy the output and paste it as the `YOUTUBE_TOKEN_B64` secret.

4. Go to **Actions** tab → enable workflows
5. The bot now runs daily automatically! ✅

**Change the schedule** in `.github/workflows/auto_upload.yml`:
```yaml
- cron: "0 10 * * *"     # Daily at 10:00 AM UTC (3:30 PM IST)
- cron: "0 10 * * 1"     # Every Monday only
- cron: "0 10 */2 * *"   # Every 2 days
```

---

### Option B: Windows Task Scheduler (runs on your PC)

1. Edit `run_bot.bat` — update `PROJECT_DIR` and `GEMINI_API_KEY`
2. Open **Task Scheduler** → **Create Basic Task**
3. Name: `YouTube Bot`
4. Trigger: **Daily** → set your time
5. Action: **Start a program** → browse to `run_bot.bat`
6. Click **Finish**

> ⚠️ Your PC must be ON and connected to the internet at the scheduled time.

---

### Option C: Linux/Mac Cron Job

1. Edit `run_bot.sh` — update the path and API key
2. Make it executable: `chmod +x run_bot.sh`
3. Open crontab: `crontab -e`
4. Add this line (runs daily at 10 AM):
   ```
   0 10 * * * /full/path/to/youtube_bot/run_bot.sh
   ```

---

## ⚙️ Configuration Reference

### Change voice style
Open `scripts/generate_voice.py`:

```python
VOICE = "en-US-GuyNeural"     # US male — natural
VOICE = "en-US-JennyNeural"   # US female — friendly
VOICE = "en-GB-RyanNeural"    # UK male — professional
VOICE = "en-AU-WilliamNeural" # Australian male
VOICE = "en-IN-NeerjaNeural"  # Indian English female

RATE  = "+10%"   # Speak 10% faster (default: +0%)
PITCH = "-3Hz"   # Slightly deeper voice (default: +0Hz)
```

### Change channel branding
Open `scripts/generate_video.py`:

```python
CHANNEL_NAME = "Your Channel Name"    # Shown in orange title bar
ACCENT_COLOR = (230, 130, 30)         # Orange — change to any RGB
BG_COLOR     = (245, 242, 235)        # Warm white background
```

### Change upload privacy
Open `scripts/upload_youtube.py`:

```python
DEFAULT_PRIVACY  = "private"    # Use "private" for testing
DEFAULT_PRIVACY  = "public"     # Use "public" for live uploads
DEFAULT_CATEGORY = CATEGORY["education"]   # Change to your niche
```

### Change video topics
Open `main.py` and edit the `TOPICS` list. Add as many as you want — the bot cycles through them automatically.

---

## 🐛 Troubleshooting

### `FFmpeg not found`
```bash
pip install imageio[ffmpeg]
```
Or download from https://ffmpeg.org and add to PATH.

### `Gemini API quota exceeded`
- Wait 24 hours (resets daily at midnight UTC)
- Create a new API key from a new Google project at aistudio.google.com
- Use `--offline` mode for testing

### `client_secrets.json not found`
- Download credentials from Google Cloud Console
- Rename to exactly `client_secrets.json`
- Place in the same folder as `main.py`

### `YouTube upload failed: quota exceeded`
- YouTube API allows ~6 uploads per day on free tier
- Wait 24 hours for quota to reset

### `ModuleNotFoundError`
```bash
pip install -r requirements.txt
```

### Video generates but looks wrong
- Open `output/slides/` to see individual PNG frames
- Adjust `CHANNEL_NAME`, font sizes in `generate_video.py`

---

## 📊 Free Tier Limits Summary

| Service | Free Limit | Needed/Day | Safe? |
|---------|------------|------------|-------|
| Gemini API | 1,500 req/day | 1 | ✅ Yes |
| YouTube API | 10,000 units/day | ~1,600 | ✅ Yes |
| GitHub Actions | 2,000 min/month | ~5 min | ✅ Yes |
| Edge TTS | Unlimited | 1 | ✅ Yes |
| Pollinations.ai | Unlimited | ~3 | ✅ Yes |

---

## 🗺️ Roadmap

- [ ] Background music support
- [ ] Custom thumbnail generation
- [ ] Multi-language support
- [ ] Analytics dashboard
- [ ] Auto-reposting to Instagram Reels and TikTok

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

## 🙏 Credits

Built with:
- [Google Gemini API](https://aistudio.google.com) — AI script generation
- [Microsoft Edge TTS](https://github.com/rany2/edge-tts) — Free voiceover
- [Pollinations.ai](https://pollinations.ai) — Free AI image generation
- [MoviePy](https://zulko.github.io/moviepy/) — Video assembly
- [YouTube Data API v3](https://developers.google.com/youtube/v3) — Auto upload

---

<div align="center">

**⭐ Star this repo if it helped you!**

Built by [Jaya Vardhan Reddy](https://github.com/YOUR_USERNAME) · [Medium Article](https://medium.com) · [YouTube Channel](#)

</div>
