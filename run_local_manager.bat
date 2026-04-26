@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "local_manager.py"
    goto :eof
)

where python >nul 2>nul
if %errorlevel%==0 (
    python "local_manager.py"
    goto :eof
)

echo Python が見つかりませんでした。
echo Python 3 をインストールしてから再実行してください。
pause
