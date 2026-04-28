@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    :: start を使うことで、Pythonを別プロセスとして切り離して起動します
    start "" pyw -3 "local_manager.py"
    goto :success
)

where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "local_manager.py"
    goto :success
)

where python >nul 2>nul
if %errorlevel%==0 (
    :: /b を抜いた start "" で完全に分離します
    start "" python "local_manager.py"
    goto :success
)

echo Python が見つかりませんでした。
echo Python 3 をインストールしてから再実行してください。
pause
goto :error

:success
:: 起動に成功したら、このバッチウィンドウ自体を即座に閉じます
exit

:error
exit /b 1