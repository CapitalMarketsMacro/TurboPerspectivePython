@echo off
echo Stopping FX Executions Blotter Server...

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8080" ^| findstr "LISTENING"') do (
    echo Killing process PID %%a
    taskkill /PID %%a /F
)

echo Done.
