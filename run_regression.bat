@echo off
setlocal enabledelayedexpansion

set ROOT_DIR=%~dp0
set BASELINE_FILE=%ROOT_DIR%regression_baseline.sample.json
set OUTPUT_FILE=%ROOT_DIR%regression_results.json

python "%ROOT_DIR%regression_suite.py" --baseline "%BASELINE_FILE%" --output "%OUTPUT_FILE%" %*
if errorlevel 1 (
  echo Regression suite failed.
  exit /b 1
)

echo Regression suite passed.
exit /b 0
