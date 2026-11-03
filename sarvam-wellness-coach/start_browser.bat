@echo off
title Aura Voice Wellness Coach
cd /d "%~dp0"
echo ========================================================
echo   Launching Aura Voice Wellness Coach in your browser...
echo   URL: http://localhost:8080
echo ========================================================
start "" http://localhost:8080
python server.py
pause
