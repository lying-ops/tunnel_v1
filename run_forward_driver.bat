@echo off
cd /d %~dp0
set PYTHONPATH=%CD%\src
py -3 src\forward_server.py
if errorlevel 1 python src\forward_server.py
pause
