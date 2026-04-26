@echo off
cd /d "%~dp0"
echo 🚀 Starte Canon Pro Web-App...
echo 📱 iPhone-Zugriff aktiviert (Adresse 0.0.0.0)
echo.
python -m streamlit run web_app.py --server.address 0.0.0.0 --server.headless true
pause