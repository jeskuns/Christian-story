@echo off
cd /d "%~dp0"

REM Christian Story - global story collection + build + publish
set LOGFILE=logs\daily_update.log
if not exist logs mkdir logs

set PYEXE=
where python >nul 2>&1
if %errorlevel%==0 set PYEXE=python
if not defined PYEXE (
  where py >nul 2>&1
  if %errorlevel%==0 set PYEXE=py
)
if not defined PYEXE (
  echo ERROR: Python not found in PATH
  exit /b 1
)

echo [%date% %time%] ==== global collection start ==== >> "%LOGFILE%"
%PYEXE% run.py full --workers 8 >> "%LOGFILE%" 2>&1
if errorlevel 1 (
  echo Collection failed. See %LOGFILE%
  type "%LOGFILE%"
  exit /b 1
)

git add site data config >> "%LOGFILE%" 2>&1
git diff --cached --quiet
if errorlevel 1 (
  git -c user.name="ChristianStory Bot" -c user.email="bot@users.noreply.github.com" commit -m "chore: global story collection" >> "%LOGFILE%" 2>&1
  git push origin master >> "%LOGFILE%" 2>&1
  if errorlevel 1 (
    echo WARN: git push failed, check credentials
  ) else (
    echo Published. Push triggers Cloudflare Pages deploy.
  )
) else (
  echo No new stories today.
)

echo [%date% %time%] ==== collection done ==== >> "%LOGFILE%"
exit /b 0
