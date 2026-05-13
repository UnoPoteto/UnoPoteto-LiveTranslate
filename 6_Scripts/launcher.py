# Whisper_2O_V2 Launcher
# - relative-path (no hardcoded BASE_DIR)
# - start/stop EN->JA(B2), JA->EN(B3), STT(B1)

import os
import subprocess
import tkinter as tk
from tkinter import messagebox

# ==== パス解決（V2フォルダに置けば自動で合う）====
SCRIPT_DIR = os.path.dirname(__file__)                   # ...\Whisper_2O_V2\Scripts
BASE_DIR   = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))  # ...\Whisper_2O_V2
PYEXE      = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")

# ==== 既定パラメータ（必要ならUI側で後から拡張してもOK）====
EN2JA_ARGS = [
    "--mode", "translate",
    "--direction", "en2ja",
    "--model", "small",
    "--input-name", "B2",
    "--speak",
    "--voice", "alloy",
    "--block-sec", "2.8",
    "--min-interval", "0.6",
    "--caption", "dst",
]

JA2EN_ARGS = [
    "--mode", "translate",
    "--direction", "ja2en",
    "--model", "small",
    "--input-name", "B3",
    "--language", "ja",
    "--speak",
    "--voice", "alloy",
    "--block-sec", "2.8",
    "--min-interval", "0.6",
    "--caption", "dst",
]

# 追加：文字起こし（翻訳なし）
STT_B1_ARGS = [
    "--mode", "stt",
    "--direction", "en2ja",   # sttでは実質意味は薄い（src_lang初期値用）
    "--model", "small",
    "--input-name", "B1",
    "--min-words", "1",
    "--block-sec", "2.8",
    "--min-interval", "0.4",
    "--caption", "src",       # OBS表示は文字起こし
]

# ==== ここから下は基本いじらなくてOK ====
CREATE_NEW_CONSOLE = 0x00000010

procs = {
    "en2ja": None,
    "ja2en": None,
    "stt_b1": None,
}

def check_paths() -> bool:
    if not os.path.exists(PYEXE):
        messagebox.showerror("エラー", f"Pythonが見つかりません:\n{PYEXE}")
        return False
    if not os.path.exists(os.path.join(SCRIPT_DIR, "main.py")):
        messagebox.showerror("エラー", f"main.py が見つかりません:\n{SCRIPT_DIR}")
        return False
    return True

def start_mode(key: str, args_list: list):
    if not check_paths():
        return
    if procs[key] is not None and procs[key].poll() is None:
        messagebox.showinfo("情報", f"{key} はすでに実行中です。")
        return
    cmd = [PYEXE, "-X", "utf8", "main.py"] + args_list
    try:
        p = subprocess.Popen(
            cmd,
            cwd=SCRIPT_DIR,
            creationflags=CREATE_NEW_CONSOLE
        )
        procs[key] = p
        update_status()
    except Exception as e:
        messagebox.showerror("起動エラー", f"{key} の起動に失敗しました。\n{e}")

def stop_mode(key: str):
    p = procs.get(key)
    if p is None or p.poll() is not None:
        procs[key] = None
        update_status()
        return
    try:
        p.terminate()
        try:
            p.wait(timeout=2)
        except Exception:
            p.kill()
    except Exception as e:
        messagebox.showerror("停止エラー", f"{key} の停止に失敗しました。\n{e}")
    finally:
        procs[key] = None
        update_status()

def stop_all():
    stop_mode("en2ja")
    stop_mode("ja2en")
    stop_mode("stt_b1")

def update_status():
    def label_of(p):
        if p is None:
            return "停止中"
        code = p.poll()
        return "実行中 (PID: {})".format(p.pid) if code is None else f"終了 (code={code})"

    lbl_en2ja_var.set(label_of(procs["en2ja"]))
    lbl_ja2en_var.set(label_of(procs["ja2en"]))
    lbl_stt_var.set(label_of(procs["stt_b1"]))

# ==== UI ====
root = tk.Tk()
root.title("Whisper_2O_V2 Launcher")

frm = tk.Frame(root, padx=14, pady=12)
frm.pack()

# EN→JA
tk.Label(frm, text="EN → JA（B2）").grid(row=0, column=0, sticky="w")
lbl_en2ja_var = tk.StringVar(value="停止中")
tk.Label(frm, textvariable=lbl_en2ja_var).grid(row=0, column=1, sticky="w", padx=10)
tk.Button(frm, text="開始", width=12,
          command=lambda: start_mode("en2ja", EN2JA_ARGS)).grid(row=1, column=0, pady=6, sticky="w")
tk.Button(frm, text="停止", width=12,
          command=lambda: stop_mode("en2ja")).grid(row=1, column=1, pady=6, sticky="w")

# JA→EN
tk.Label(frm, text="JA → EN（B3）").grid(row=2, column=0, sticky="w", pady=(12,0))
lbl_ja2en_var = tk.StringVar(value="停止中")
tk.Label(frm, textvariable=lbl_ja2en_var).grid(row=2, column=1, sticky="w", padx=10, pady=(12,0))
tk.Button(frm, text="開始", width=12,
          command=lambda: start_mode("ja2en", JA2EN_ARGS)).grid(row=3, column=0, pady=6, sticky="w")
tk.Button(frm, text="停止", width=12,
          command=lambda: stop_mode("ja2en")).grid(row=3, column=1, pady=6, sticky="w")

# STT
tk.Label(frm, text="文字起こし（B1）").grid(row=4, column=0, sticky="w", pady=(12,0))
lbl_stt_var = tk.StringVar(value="停止中")
tk.Label(frm, textvariable=lbl_stt_var).grid(row=4, column=1, sticky="w", padx=10, pady=(12,0))
tk.Button(frm, text="開始", width=12,
          command=lambda: start_mode("stt_b1", STT_B1_ARGS)).grid(row=5, column=0, pady=6, sticky="w")
tk.Button(frm, text="停止", width=12,
          command=lambda: stop_mode("stt_b1")).grid(row=5, column=1, pady=6, sticky="w")

# All
tk.Button(frm, text="すべて停止", width=26, command=stop_all).grid(row=6, column=0, columnspan=2, pady=(14,0))

update_status()
root.mainloop()

