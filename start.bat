@echo off
echo ==========================================
echo   EmoLearn v2 - Starting Server
echo ==========================================
cd /d "%~dp0emolearn-backend"
pip install -r requirements.txt
python app.py
pause
