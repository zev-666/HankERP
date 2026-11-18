@echo off
rem EVEREVO ERP offline edition - see offline\README.md
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0erp.ps1" backup
echo.
pause
