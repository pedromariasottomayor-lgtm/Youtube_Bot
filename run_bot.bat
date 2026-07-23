@echo off
REM ─────────────────────────────────────────────────────────────────
REM  run_bot.bat — Windows Task Scheduler launcher
REM  Set this file in Windows Task Scheduler to run on a schedule
REM  See SETUP_GUIDE.txt for full instructions
REM ─────────────────────────────────────────────────────────────────

REM Navigate to project folder (change this path to your actual folder)
cd /d "C:\youtube_bot"

REM Activate virtual environment (if you created one)
REM Uncomment the line below if you used: python -m venv venv
REM call venv\Scripts\activate.bat

REM Set your Gemini API key (or set it as a system environment variable)
set GEMINI_API_KEY=your_gemini_api_key_here

REM Run the bot
python main.py

REM Log the result
echo Run completed at %date% %time% >> run_log.txt
