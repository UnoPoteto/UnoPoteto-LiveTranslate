@echo off
setlocal EnableExtensions

rem ============================================================
rem Whisper_2O_V2 - run_mini_toggle.bat
rem 目的:
rem   - V2 の .venv を使って mini_toggle.py（運用用1ボタンUI）を起動
rem   - V1/V2混在事故を防ぐため、相対パスで解決する
rem ============================================================

rem --- This bat is placed under: ...\Whisper_2O_V2\Scripts\
set "SCRIPTS_DIR=%~dp0"
set "BASE_DIR=%SCRIPTS_DIR%.."
for %%I in ("%BASE_DIR%") do set "BASE_DIR=%%~fI"

set "PYEXE=%BASE_DIR%\.venv\Scripts\python.exe"
set "TOGGLE_PY=%SCRIPTS_DIR%mini_toggle.py"

if not exist "%PYEXE%" (
  echo [ERROR] Python not found:
  echo   %PYEXE%
  echo [HINT] .venv が作成されているか確認してください。
  pause
  exit /b 1
)

if not exist "%TOGGLE_PY%" (
  echo [ERROR] mini_toggle.py not found:
  echo   %TOGGLE_PY%
  pause
  exit /b 1
)

pushd "%SCRIPTS_DIR%"

rem --- GUI起動なので新しいコンソールは基本不要。
"%PYEXE%" -X utf8 "%TOGGLE_PY%"

popd
exit /b 0

