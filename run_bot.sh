#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# run_bot.sh — Linux/Mac cron launcher
# Add to crontab with: crontab -e
# Then add this line to run daily at 10am:
#   0 10 * * * /path/to/youtube_bot/run_bot.sh
# ─────────────────────────────────────────────────────────────────

# Navigate to project folder (change this path)
cd /home/yourname/youtube_bot

# Activate virtual environment (if you created one)
# source venv/bin/activate

# Set your Gemini API key
export GEMINI_API_KEY="your_gemini_api_key_here"

# Run the bot
/usr/bin/python3 main.py

# Log the result
echo "Run completed at $(date)" >> run_log.txt
