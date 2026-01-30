@echo off
chcp 65001 >nul
echo ========================================
echo Yu-Gi-Oh! Master Duel - 调试 UI
echo ========================================
echo.

echo 正在检查依赖...
python -c "import PyQt5" 2>nul
if errorlevel 1 (
    echo [错误] PyQt5 未安装
    echo 正在安装 PyQt5...
    pip install PyQt5
)

python -c "from ppadb.client import Client" 2>nul
if errorlevel 1 (
    echo [警告] pure-python-adb 未安装，将使用命令行模式
    echo 建议安装以获得更好的性能: pip install pure-python-adb
    echo.
)

echo 正在启动调试 UI...
echo.
python debug_ui.py

if errorlevel 1 (
    echo.
    echo [错误] 启动失败
    pause
)
