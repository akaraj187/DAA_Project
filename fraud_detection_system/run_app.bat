@echo off
echo Starting FraudGuard AI...
echo checking dependencies...
pip install -r requirements.txt
cls
echo Dependencies checked. Launching Server...
echo.
echo ===================================================
echo OPEN YOUR BROWSER TO: http://127.0.0.1:5000
echo ===================================================
echo.
python app.py
pause
