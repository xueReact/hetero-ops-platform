@echo off
cd /d "%~dp0"
docker compose --profile airport stop
if errorlevel 1 pause
