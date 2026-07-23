@echo off
chcp 65001 >nul
REM ============================================================
REM 网安智盾 Windows 版 — 一键打包脚本
REM 用法：双击本文件 或 在命令行运行
REM       传 --console 参数可打包带控制台窗口的版本（用于调试）
REM 前置：已安装 Python 3.11 64位 并勾选 "Add to PATH"
REM 产出：dist\WangAnZhiDun\ （目录版，含 WangAnZhiDun.exe）
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
REM 透传命令行参数（如 --console）给 build.spec
pyinstaller build.spec %*

if exist dist\WangAnZhiDun\WangAnZhiDun.exe (
    echo.
    echo ========================================
    echo  打包完成！
    echo  运行：%CD%\dist\WangAnZhiDun\WangAnZhiDun.exe
    echo  目录：%CD%\dist\WangAnZhiDun\
    echo ========================================
) else (
    echo 打包似乎失败，请检查上方报错。
)
pause
endlocal
