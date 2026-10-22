@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if not exist "data\temp" mkdir "data\temp"
set "TEMP=%~dp0data\temp"
set "TMP=%TEMP%"
set "PYTHONDONTWRITEBYTECODE=1"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "PIP_CACHE_DIR=%~dp0data\pip-cache"
set "PYTHON_EXE="
set "PYTHON_FLAGS="
where py >nul 2>nul
if not errorlevel 1 (
  set "PYTHON_EXE=py"
  set "PYTHON_FLAGS=-3"
) else (
  where python >nul 2>nul
  if not errorlevel 1 set "PYTHON_EXE=python"
)
if not defined PYTHON_EXE (
  echo 未找到 Python。只想玩游戏请返回上级目录打开“奶龙外卖.exe”。
  echo 修改源码需要安装 Windows 64 位 Python，建议 3.13。
  pause
  exit /b 1
)
"%PYTHON_EXE%" %PYTHON_FLAGS% -B -m pip install --target "%~dp0.packaging" --cache-dir "%PIP_CACHE_DIR%" --only-binary=:all: -r requirements-build.txt
if errorlevel 1 (echo 安装失败。) else (echo 安装完成，可运行重新打包.bat。)
pause

endlocal
