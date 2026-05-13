' ============================================================
' Whisper_2O_V2 - run_mini_toggle_hidden.vbs
' 目的:
'   - コンソールを表示せずに mini_toggle.py を起動する
'   - V1/V2混在事故を防ぐため、スクリプトの場所から相対で解決する
' ============================================================

Option Explicit

Dim oWS, scriptDir, baseDir, pyExe, togglePy, cmd

Set oWS = CreateObject("WScript.Shell")

' この .vbs が置かれているフォルダ（= Scripts）を取得
scriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' baseDir = Scripts\.. （= Whisper_2O_V2）
baseDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(scriptDir)

pyExe    = baseDir & "\.venv\Scripts\python.exe"
togglePy = scriptDir & "\mini_toggle.py"

' 実行カレントを Scripts にする（相対参照・ログ出力などのため）
oWS.CurrentDirectory = scriptDir

' 0 = ウィンドウ非表示, False = 待たない
cmd = """" & pyExe & """ -X utf8 """ & togglePy & """"
oWS.Run cmd, 0, False

