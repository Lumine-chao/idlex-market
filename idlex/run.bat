@echo off
chcp 65001 >nul
cd /d "%~dp0"
setlocal

set "PORT=8000"
set "URL=http://127.0.0.1:%PORT%"
set "PIDFILE=%~dp0run.pid"

echo ============================================
echo   闲置易 · 二手交易平台 - 启动服务
echo ============================================
echo.

REM ---------- 已在运行则直接打开浏览器 ----------
call :listening
if "%LISTENING%"=="1" (
  echo [提示] 服务已在运行，直接打开浏览器。
  start "" "%URL%"
  echo.
  pause
  exit /b 0
)

REM ---------- 1) 准备后端虚拟环境 ----------
if not exist "backend\.venv\Scripts\python.exe" (
  echo [1/4] 创建后端虚拟环境...
  python -m venv backend\.venv
  if not exist "backend\.venv\Scripts\python.exe" (
    echo [错误] 创建虚拟环境失败，请先安装 Python 3.11+ 并加入 PATH。
    echo.
    pause
    exit /b 1
  )
)

REM ---------- 2) 安装 / 校验后端依赖 ----------
echo [2/4] 安装 / 校验后端依赖...
"backend\.venv\Scripts\python.exe" -m pip install -r backend\requirements.txt --disable-pip-version-check -q
if errorlevel 1 (
  echo [错误] 安装后端依赖失败，请检查网络或 requirements.txt。
  echo.
  pause
  exit /b 1
)

REM ---------- 3) 前端构建产物 ----------
if not exist "web\dist\index.html" (
  echo [3/4] 构建前端产物（首次较慢）...
  pushd web
  call npm install
  if errorlevel 1 (
    popd
    echo [错误] npm install 失败，请确认已安装 Node.js。
    echo.
    pause
    exit /b 1
  )
  call npm run build
  if errorlevel 1 (
    popd
    echo [错误] 前端构建失败。
    echo.
    pause
    exit /b 1
  )
  popd
) else (
  echo [3/4] 前端产物已存在，跳过构建
)

REM ---------- 4) 后台启动后端 ----------
echo [4/4] 启动后端服务...
set "IDLEX_PY=%~dp0backend\.venv\Scripts\python.exe"
set "IDLEX_DIR=%~dp0backend"
set "IDLEX_PID=%~dp0run.pid"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$p = Start-Process -FilePath $env:IDLEX_PY -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','%PORT%' -WorkingDirectory $env:IDLEX_DIR -WindowStyle Minimized -PassThru; $p.Id | Out-File -Encoding ascii -LiteralPath $env:IDLEX_PID"
if errorlevel 1 (
  echo [错误] 启动后端进程失败，请检查虚拟环境与依赖。
  echo.
  pause
  exit /b 1
)

REM ---------- 等待服务就绪 ----------
set /a TRIES=0
:wait
call :listening
if "%LISTENING%"=="1" goto ready
set /a TRIES+=1
if %TRIES% geq 30 goto timeout
ping -n 2 127.0.0.1 >nul 2>&1
goto wait

:timeout
echo [警告] 等待服务就绪超时，后端可能启动失败，请查看最小化的服务窗口日志。
echo.
pause
exit /b 1

:ready
set "PID="
for /f "usebackq" %%a in ("%PIDFILE%") do set "PID=%%a"
echo.
echo [完成] 服务已启动（PID %PID%），正在打开浏览器...
echo        访问地址：%URL%
echo        停止服务：双击 stop.bat
start "" "%URL%"
echo.
pause
exit /b 0

:listening
set "LISTENING=0"
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do set "LISTENING=1"
exit /b 0