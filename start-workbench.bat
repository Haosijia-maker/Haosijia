@echo off
cd /d "%~dp0"
set PORT=8848
set BIND=0.0.0.0
set PY=C:\Users\ADMIN\.workbuddy\binaries\python\versions\3.13.12\python.exe
if not exist "%PY%" set PY=python

REM 若端口已在运行，直接打开浏览器，避免重复启动
netstat -ano 2>nul | findstr ":8848" | findstr "LISTENING" >nul
if %errorlevel%==0 (
  echo 检测到 8848 端口已在运行，直接打开浏览器。
  start "" http://127.0.0.1:8848/
  goto :eof
)

echo 正在启动思嘉工作台 ...
start "" "%PY%" server.py
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:8848/
echo 思嘉工作台已启动（http://127.0.0.1:8848/）。
echo 关闭弹出的服务窗口即可停止；或运行 stop-workbench.bat 停止。
