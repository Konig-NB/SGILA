@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.12 or newer and try again.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  python -m venv .venv || goto :error
)

echo Installing required packages...
".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :error

echo Preparing the database...
".venv\Scripts\python.exe" manage.py migrate || goto :error
".venv\Scripts\python.exe" manage.py load_curriculum_content || goto :error
".venv\Scripts\python.exe" manage.py sync_grade2_activities || goto :error
".venv\Scripts\python.exe" manage.py check || goto :error

echo Starting SGILA at http://127.0.0.1:8000/
".venv\Scripts\python.exe" manage.py runserver
exit /b %errorlevel%

:error
echo.
echo SGILA setup failed. Review the message above.
pause
exit /b 1
