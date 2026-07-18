@echo off
chcp 65001 >nul
REM ============================================================
REM 网安智盾 · 推送到 GitHub
REM 前置：已执行 `gh auth login` 完成登录（浏览器授权）
REM 仓库名默认 wanganzhidun，可改下面一行
REM ============================================================
set REPO=wanganzhidun

echo [网安智盾] 检查 gh 登录 ...
gh auth status >nul 2>&1
if errorlevel 1 (
    echo 请先运行：gh auth login
    pause
    exit /b 1
)

echo [网安智盾] 创建仓库并推送（公开）...
gh repo create %REPO% --public --source=. --remote=origin --push

if errorlevel 1 (
    echo 创建/推送失败，可能仓库名已存在，或需先 git remote add。
    echo 手动方式：git remote add origin https://github.com/你的用户名/%REPO%.git ^&^& git push -u origin main
) else (
    echo.
    echo 完成！仓库已开源：https://github.com/你的用户名/%REPO%
)
pause
