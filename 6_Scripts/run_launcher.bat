@echo off
setlocal EnableExtensions

rem ============================================================
rem Whisper_2O_V2 - run_launcher.bat
rem 目的:
rem   - V2 の .venv を使って launcher.py（簡易ランチャーUI）を起動
rem   - V1/V2混在事故を防ぐため、相対パスで解決する
rem ============================================================

rem --- This bat is placed under: ...\Whisper_2O_V2\Scripts\
set "SCRIPTS_DIR=%~dp0"
set "BASE_DIR=%SCRIPTS_DIR%.."
for %%I in ("%BASE_DIR%") do set "BASE_DIR=%%~fI"

set "PYEXE=%BASE_DIR%\.venv\Scripts\python.exe"
set "LAUNCHER_PY=%SCRIPTS_DIR%launcher.py"

if not exist "%PYEXE%" (
  echo [ERROR] Python not found:
  echo   %PYEXE%
  echo [HINT] .venv が作成されているか確認してください。
  pause
  exit /b 1
)

if not exist "%LAUNCHER_PY%" (
  echo [ERROR] launcher.py not found:
  echo   %LAUNCHER_PY%
  pause
  exit /b 1
)

pushd "%SCRIPTS_DIR%"

rem --- GUI起動なので新しいコンソールは基本不要。必要なら start "" で分離も可能。
"%PYEXE%" -X utf8 "%LAUNCHER_PY%"

popd
exit /b 0
