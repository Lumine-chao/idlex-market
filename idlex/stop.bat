@echo off
chcp 65001 >nul
cd /d "%~dp0"
setlocal enabledelayedexpansion

set "PORT=8000"
set "PIDFILE=%~dp0run.pid"
set "STOPPED=0"

echo ============================================
echo   闲置易 · 二手交易平台 - 停止服务
echo ============================================
echo.

REM ---------- 1) 优先按 PID 文件精确停止 ----------
if exist "%PIDFILE%" (
  set "PID="
  for /f "usebackq" %%a in ("%PIDFILE%") do set "PID=%%a"
  if defined PID (
    taskkill /F /T /PID !PID! >nul 2>&1
    if !errorlevel! equ 0 (
      echo [完成] 已停止后端进程（PID !PID!）
      set "STOPPED=1"
    )
  )
  del /f /q "%PIDFILE%" >nul 2>&1
)

REM ---------- 2) 兜底：按端口清理残留进程 ----------
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
  taskkill /F /T /PID %%a >nul 2>&1
  if !errorlevel! equ 0 (
    echo [完成] 已停止占用 %PORT% 端口的进程（PID %%a）
    set "STOPPED=1"
  )
)

echo.
if "!STOPPED!"=="1" (
  echo 服务已停止。
) else (
  echo 未发现正在运行的服务。
)
echo.
pause