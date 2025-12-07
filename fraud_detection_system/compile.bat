@echo off
echo Compiling Fraud Engine...
g++ -o fraud_engine.exe fraud_engine.cpp
if %errorlevel% neq 0 (
    echo Compilation Failed!
    exit /b %errorlevel%
)
echo Compilation Successful.
echo.
echo You can now run the backend with: python app.py
pause
