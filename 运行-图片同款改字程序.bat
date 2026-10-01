@echo off
chcp 65001 >nul
title 智能图片改字程序
cd /d "%~dp0"

echo ======================================================
echo 正在启动 智能图片改字程序...
echo ======================================================

if exist "image_text_replacer.html" (
    start image_text_replacer.html
) else (
    python run_text_replacer.py
)

exit
