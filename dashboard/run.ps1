# KR Pension Self-Driving SAA Dashboard launcher (PowerShell)
# Port 8504 (avoids kr_dashboard:8501, barbell:8503)

$env:PYTHONIOENCODING = "utf-8"
Set-Location $PSScriptRoot

Write-Host "[run.ps1] Starting Streamlit on port 8504 ..." -ForegroundColor Cyan
Write-Host "[run.ps1] URL: http://localhost:8504" -ForegroundColor Cyan
Write-Host ""

$py = "d:\파이선\pykrx_venv\Scripts\python.exe"
& $py -m streamlit run app.py --server.port 8504 --browser.gatherUsageStats false
