@echo off
chcp 65001 >nul
REM ============================================================
REM 网安智盾 Windows 版 — 一键打包脚本
REM 用法：在 Windows 10/11 (64位) 上双击本文件
REM 前置：已安装 Python 3.11 64位 并勾选 "Add to PATH"
REM 产出：dist\WangAnZhiDun.exe （单文件、无控制台窗口）
REM ============================================================
setlocal

echo [网安智盾] 检查 Python ...
where python >nul 2>&1
if errorlevel 1 (
    echo 未检测到 Python，请先安装 Python 3.11 64位 并勾选 Add to PATH
    pause
    exit /b 1
)

echo [网安智盾] 创建虚拟环境 ...
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate.bat

echo [网安智盾] 升级 pip 并安装依赖 ...
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo [网安智盾] 开始 PyInstaller 打包 ...
pyinstaller build.spec

if exist dist\WangAnZhiDun.exe (
    echo.
    echo ========================================
    echo  打包完成！exe 位于：
    echo  %CD%\dist\WangAnZhiDun.exe
    echo ========================================
) else (
    echo 打包似乎失败，请检查上方报错。
)
pause
endlocal
