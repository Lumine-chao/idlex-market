@echo off
chcp 65001 >nul
cd /d %~dp0
echo ============================================
echo   闲置易 - 二手交易平台 一键启动
echo ============================================
echo.

if not exist backend\.venv (
  echo [1/3] 创建后端虚拟环境...
  python -m venv backend\.venv || (echo 请先安装 Python 3.11+ & pause & exit /b 1)
)
call backend\.venv\Scripts\activate.bat

echo [1/3] 安装后端依赖...
pip install -r backend\requirements.txt >nul 2>&1

if not exist web\dist\index.html (
  echo [2/3] 构建前端产物（首次或前端改动后需要）...
  pushd web
  call npm install
  call npm run build
  popd
) else (
  echo [2/3] 前端产物已存在，跳过构建
)

echo [3/3] 启动后端（自动托管前端）...
echo 请稍候，浏览器将打开 http://127.0.0.1:8000
start "" http://127.0.0.1:8000
pushd backend
set PYTHONPATH=%~dp0backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
popd