@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Bilibili Content Extractor
python bili_quick.py
pause
