@echo off
chcp 65001 >nul
title 批量图片体积压缩瘦身工坊 (自动保存至原图目录 · 严格 <= 10MB)

echo.
echo ======================================================================
echo    ⚡ 批量图片体积压缩瘦身工坊 (默认导出位置：图片本身的所在目录)
echo ======================================================================
echo.
echo 💡 导出模式：每张图片压缩后，自动写回该图片本身的所在目录
echo 🛡️ 体积控制：严格限制单张导出体积不超过 10MB (或自定义上限)
echo.
echo 正在启动工具，请稍候...

python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    python "%~dp0batch_image_compressor.py" --gui
) else (
    echo [提示] 未检测到 Python 环境，正在通过系统浏览器直接打开...
    start "" "%~dp0batch_image_compressor.html"
)
exit
