@echo off
echo 正在停止思嘉工作台（端口 8848）...
for /f "tokens=5" %%P in ('netstat -ano 2^>nul ^| findstr "LISTENING" ^| findstr ":8848"') do (
  taskkill /PID %%P /F >nul 2>&1 && echo 已停止进程 PID %%P
)
echo 完成。若提示“未找到”，说明服务当前未运行。
pause
