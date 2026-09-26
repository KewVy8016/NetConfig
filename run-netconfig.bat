@echo off
rem NetConfig — เปิด Backend และ Frontend ด้วยคลิกเดียว
setlocal

set "PROJECT_ROOT=%~dp0"
set "PYTHON_EXE=C:\Users\Thanaboon\AppData\Local\Programs\Python\Python311\python.exe"

rem ไม่เปิดซ้ำเมื่อ Backend เดิมยังตอบอยู่ (เช่น process ที่ Codex รีสตาร์ตไว้)
curl.exe -fsS --max-time 2 "http://127.0.0.1:8000/health" 2>nul | findstr /C:"netconfig" >nul
if errorlevel 1 (
    if exist "%PYTHON_EXE%" (
        start "NetConfig Backend" /D "%PROJECT_ROOT%" cmd /k ""%PYTHON_EXE%" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"
    ) else (
        rem ใช้ Python Launcher เป็น fallback หาก path Python เฉพาะเครื่องเปลี่ยน
        start "NetConfig Backend" /D "%PROJECT_ROOT%" cmd /k "py -3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"
    )
) else (
    echo NetConfig Backend is already running on port 8000.
)

rem Vite จะเปลี่ยนพอร์ตเองหาก 5175 ถูกใช้ จึงตรวจและไม่เปิดซ้ำ
curl.exe -fsS --max-time 2 "http://127.0.0.1:5175/" >nul 2>&1
if errorlevel 1 (
    start "NetConfig Frontend" /D "%PROJECT_ROOT%frontend" cmd /k "npm run dev -- --host 127.0.0.1 --port 5175 --strictPort"
) else (
    echo NetConfig Frontend is already running on port 5175.
)

rem รอให้ Vite เริ่มฟังพอร์ต ก่อนเปิด Browser
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:5175/"

endlocal
