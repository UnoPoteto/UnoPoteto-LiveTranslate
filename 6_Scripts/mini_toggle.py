# ============================================================
# Whisper_2O_V2 - Mini Toggle Launcher (Production Version)
#
# 役割:
#   - 1ボタンで翻訳モードを切り替える「運用用ミニUI」
#   - OFF : EN -> JA（受信翻訳 / B2）
#   - ON  : JA -> EN（送信翻訳 / マイク）
#
# 設計方針:
#   - 設定変更はしない（迷わない）
#   - 常に最前面（VR / 配信向け）
#   - 二重起動を防止
#   - Whisper_2O_V2 / main.py に完全準拠
#
# ============================================================

import os
import subprocess
import tkinter as tk
from tkinter import messagebox

# ------------------------------------------------------------
# パス解決（V2専用・相対パス）
# ------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(__file__)                 # ...\Whisper_2O_V2\Scripts
BASE_DIR   = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
PYTHON_EXE = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")
MAIN_PY    = os.path.join(SCRIPT_DIR, "main.py")

CREATE_NEW_CONSOLE = 0x00000010

# ------------------------------------------------------------
# 入力デバイス定義（※ index 固定はしない）
# ------------------------------------------------------------

# 受信翻訳（Discord / 相手の声）
RX_INPUT_NAME = "B2"        # Voicemeeter AUX Output B2

# 送信翻訳（あなたの声）
TX_INPUT_NAME = "Microphone"  # Quest / Windows マイク名（部分一致でOK）

# ------------------------------------------------------------
# Whisper 実行パラメータ（V2 main.py 準拠）
# ------------------------------------------------------------

COMMON_PARAMS = [
    "--model", "small",
    "--compute", "cuda",
]

RX_PARAMS = [
    "--mode", "translate",
    "--direction", "en2ja",
    "--input-name", RX_INPUT_NAME,
    "--block-sec", "2.6",
    "--min-interval", "0.5",
    "--caption", "dst",
]

TX_PARAMS = [
    "--mode", "translate",
    "--direction", "ja2en",
    "--input-name", TX_INPUT_NAME,
    "--language", "ja",
    "--speak",
    "--voice", "alloy",
    "--block-sec", "2.4",
    "--min-interval", "0.45",
    "--caption", "dst",
]

# ------------------------------------------------------------
# プロセス管理
# ------------------------------------------------------------

current_process = None
current_mode = "RX"   # 初期状態：受信翻訳

def start_whisper(params):
    global current_process

    if not os.path.exists(PYTHON_EXE):
        messagebox.showerror("Error", f"Python not found:\n{PYTHON_EXE}")
        return

    if not os.path.exists(MAIN_PY):
        messagebox.showerror("Error", f"main.py not found:\n{MAIN_PY}")
        return

    cmd = [PYTHON_EXE, "-X", "utf8", MAIN_PY] + COMMON_PARAMS + params

    current_process = subprocess.Popen(
        cmd,
        cwd=SCRIPT_DIR,
        creationflags=CREATE_NEW_CONSOLE
    )

def stop_whisper():
    global current_process
    if current_process is None:
        return

    try:
        current_process.terminate()
        current_process.wait(timeout=2)
    except Exception:
        try:
            current_process.kill()
        except Exception:
            pass
    finally:
        current_process = None

# ------------------------------------------------------------
# トグル処理
# ------------------------------------------------------------

def toggle():
    global current_mode

    stop_whisper()

    if current_mode == "RX":
        start_whisper(TX_PARAMS)
        current_mode = "TX"
        btn.config(text="TX ▶ 送信翻訳中", bg="#ffcccc")
    else:
        start_whisper(RX_PARAMS)
        current_mode = "RX"
        btn.config(text="RX ▶ 受信翻訳中", bg="#ccffcc")

# ------------------------------------------------------------
# UI 構築
# ------------------------------------------------------------

root = tk.Tk()
root.title("Whisper_2O_V2 Mini Toggle")
root.geometry("200x80")
root.attributes("-topmost", True)
root.resizable(False, False)

btn = tk.Button(
    root,
    text="RX ▶ 受信翻訳中",
    font=("Meiryo", 10, "bold"),
    bg="#ccffcc",
    command=toggle
)
btn.pack(expand=True, fill="both", padx=10, pady=10)

# ------------------------------------------------------------
# 起動時：RX モード自動開始
# ------------------------------------------------------------

start_whisper(RX_PARAMS)

def on_close():
    stop_whisper()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)

root.mainloop()

