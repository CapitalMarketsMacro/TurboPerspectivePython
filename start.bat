@echo off
setlocal

set SOURCE=%1
if "%SOURCE%"=="" set SOURCE=nats

if /I not "%SOURCE%"=="solace" if /I not "%SOURCE%"=="nats" (
    echo Usage: start.bat [solace^|nats]
    exit /b 1
)

echo Starting FX Executions Blotter Server [%SOURCE%]...

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo WARNING: No venv found, using system Python
)

if not exist .env (
    echo ERROR: .env file not found. Copy .env.example to .env and fill in values.
    exit /b 1
)

python server.py --source %SOURCE%
