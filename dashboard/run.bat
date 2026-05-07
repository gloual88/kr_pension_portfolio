@echo off
REM KR Pension Self-Driving SAA Dashboard launcher
REM Port 8504 (avoids kr_dashboard:8501, barbell:8503)
chcp 65001 >nul
setlocal
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

echo [run.bat] Starting Streamlit on port 8504 ...
echo [run.bat] URL: http://localhost:8504
echo.

set PY="d:\파이선\pykrx_venv\Scripts\python.exe"
%PY% -m streamlit run app.py --server.port 8504 --browser.gatherUsageStats false

endlocal
