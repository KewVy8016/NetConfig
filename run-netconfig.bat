@echo off
rem NetConfig — เปิด Backend และ Frontend ด้วยคลิกเดียว
setlocal

set "PROJECT_ROOT=%~dp0"
set "PYTHON_EXE=C:\Users\Thanaboon\AppData\Local\Programs\Python\Python311\python.exe"

if exist "%PYTHON_EXE%" (
    start "NetConfig Backend" /D "%PROJECT_ROOT%" cmd /k ""%PYTHON_EXE%" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"
) else (
    rem ใช้ Python Launcher เป็น fallback หาก path Python เฉพาะเครื่องเปลี่ยน
    start "NetConfig Backend" /D "%PROJECT_ROOT%" cmd /k "py -3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"
)

start "NetConfig Frontend" /D "%PROJECT_ROOT%frontend" cmd /k "npm run dev -- --host 127.0.0.1 --port 5175"

rem รอให้ Vite เริ่มฟังพอร์ต ก่อนเปิด Browser
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:5175/"

endlocal
