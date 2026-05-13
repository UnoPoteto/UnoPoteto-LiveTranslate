# -*- coding: utf-8 -*-
# Whisper_2O_V2 plus Launcher
# Buttons:
#   EN->JA(B2), JA->EN(B3),
#   STT(JA), STT(EN), STT(AUTO),
#   STOP ALL

import os
import sys
import json
import subprocess
import threading
import queue
import time
import tkinter as tk
from tkinter import ttk, messagebox

# ========== Paths ==========
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PY = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")
MAIN_PY = os.path.join(SCRIPTS_DIR, "main.py")
CONFIG_JSON = os.path.join(SCRIPTS_DIR, "ui_launcher_config.json")

OUTPUT_DIR = os.path.join(BASE_DIR, "output")
LOGS_DIR = os.path.join(SCRIPTS_DIR, "Logs")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# ========== Subprocess ==========
proc = None
log_q = queue.Queue()

def read_stream(stream, q, prefix=""):
    try:
        for line in iter(stream.readline, b""):
            q.put(prefix + line.decode(errors="ignore"))
    finally:
        try:
            stream.close()
        except Exception:
            pass

def run_main_py(params, env_overrides=None):
    """Launch main.py with params."""
    global proc
    if not os.path.exists(VENV_PY):
        log_q.put(f"[ERROR] python.exe not found: {VENV_PY}\n")
        return
    if not os.path.exists(MAIN_PY):
        log_q.put(f"[ERROR] main.py not found: {MAIN_PY}\n")
        return

    cmd = [VENV_PY, "-X", "utf8", MAIN_PY] + params
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=SCRIPTS_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            env=env
        )
        t = threading.Thread(target=read_stream, args=(proc.stdout, log_q, ""), daemon=True)
        t.start()
        ret = proc.wait()
        log_q.put(f"\n[INFO] Process exited with code {ret}\n")
    except Exception as e:
        log_q.put(f"[ERROR] Failed to launch: {e}\n")
    finally:
        proc = None

def stop_process():
    global proc
    p = proc
    if p is None:
        log_q.put("[INFO] No running process.\n")
        return
    try:
        if p.poll() is None:
            p.terminate()
            for _ in range(30):
                if p.poll() is not None:
                    break
                time.sleep(0.1)
            if p.poll() is None:
                subprocess.call(
                    ["taskkill", "/F", "/PID", str(p.pid)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
    except Exception as e:
        log_q.put(f"[WARN] stop error: {e}\n")
    finally:
        proc = None

# ========== Config ==========
def load_config():
    if not os.path.exists(CONFIG_JSON):
        return {}
    try:
        with open(CONFIG_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_config(cfg: dict):
    try:
        with open(CONFIG_JSON, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log_q.put(f"[WARN] Failed to save config: {e}\n")

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Whisper_2O_V2 plus Launcher")
        self.geometry("980x560")

        self.cfg = load_config()

        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=10)

        # Direction (translate用)
        ttk.Label(top, text="Direction").grid(row=0, column=0, sticky="w")
        self.direction = tk.StringVar(value=self.cfg.get("direction", "en2ja"))
        ttk.Radiobutton(top, text="EN → JA", value="en2ja", variable=self.direction, command=self.on_direction)\
            .grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(top, text="JA → EN", value="ja2en", variable=self.direction, command=self.on_direction)\
            .grid(row=0, column=2, sticky="w")

        # Model
        ttk.Label(top, text="Model").grid(row=0, column=3, sticky="e", padx=(16,0))
        self.model = tk.StringVar(value=self.cfg.get("model","small"))
        ttk.Combobox(top, textvariable=self.model,
                     values=["tiny","base","small","medium","large"],
                     width=10, state="readonly")\
            .grid(row=0, column=4, sticky="w", padx=(6,0))

        # Compute -> main.pyへは --device で渡す（autoなら渡さない）
        ttk.Label(top, text="Compute").grid(row=0, column=5, sticky="e", padx=(16,0))
        self.compute = tk.StringVar(value=self.cfg.get("compute","auto"))
        ttk.Combobox(top, textvariable=self.compute, values=["auto","cuda","cpu"],
                     width=8, state="readonly")\
            .grid(row=0, column=6, sticky="w", padx=(6,0))

        # Input device
        ttk.Label(top, text="Input").grid(row=1, column=0, sticky="w", pady=(6,0))
        self.device_mode = tk.StringVar(value=self.cfg.get("device_mode","name"))
        self.input_name = tk.StringVar(value=self.cfg.get("input_name","B2"))
        self.input_index = tk.StringVar(value=self.cfg.get("input_index",""))

        ttk.Radiobutton(top, text="by Name", value="name", variable=self.device_mode)\
            .grid(row=1, column=1, sticky="w", pady=(6,0))
        ttk.Radiobutton(top, text="by Index", value="index", variable=self.device_mode)\
            .grid(row=1, column=2, sticky="w", pady=(6,0))
        ttk.Entry(top, textvariable=self.input_name, width=30)\
            .grid(row=1, column=3, columnspan=2, sticky="we", padx=(12,0), pady=(6,0))
        ttk.Button(top, text="List Devices", command=self.list_devices)\
            .grid(row=1, column=5, sticky="w", padx=8, pady=(6,0))

        # Language + Speak + Voice
        ttk.Label(top, text="Language hint (optional)").grid(row=2, column=0, sticky="w", pady=(6,0))
        # ※ここは翻訳用ヒント（translate）として使う。STTには使わない。
        self.language = tk.StringVar(value=self.cfg.get("language",""))
        ttk.Entry(top, textvariable=self.language, width=10).grid(row=2, column=1, sticky="w", pady=(6,0))

        self.speak = tk.BooleanVar(value=self.cfg.get("speak", False))
        ttk.Checkbutton(top, text="Speak", variable=self.speak).grid(row=2, column=2, sticky="w", pady=(6,0))
        ttk.Label(top, text="Voice").grid(row=2, column=3, sticky="e", pady=(6,0))
        self.voice = tk.StringVar(value=self.cfg.get("voice","alloy"))
        ttk.Entry(top, textvariable=self.voice, width=12).grid(row=2, column=4, sticky="w", padx=6, pady=(6,0))

        # Timing
        ttk.Label(top, text="block-sec").grid(row=3, column=0, sticky="w", pady=(6,0))
        self.block_sec = tk.DoubleVar(value=float(self.cfg.get("block_sec",2.6)))
        ttk.Entry(top, textvariable=self.block_sec, width=8).grid(row=3, column=1, sticky="w", pady=(6,0))

        ttk.Label(top, text="min-interval").grid(row=3, column=2, sticky="w", pady=(6,0))
        self.min_interval = tk.DoubleVar(value=float(self.cfg.get("min_interval",0.5)))
        ttk.Entry(top, textvariable=self.min_interval, width=8).grid(row=3, column=3, sticky="w", pady=(6,0))

        # Caption
        ttk.Label(top, text="caption").grid(row=3, column=4, sticky="e", padx=(6,0), pady=(6,0))
        self.caption = tk.StringVar(value=self.cfg.get("caption","dst"))
        ttk.Combobox(top, textvariable=self.caption, values=["none","src","dst","both"],
                     width=8, state="readonly")\
            .grid(row=3, column=5, sticky="w", padx=(6,0), pady=(6,0))

        # Quick Buttons
        quick = ttk.Frame(self)
        quick.pack(fill="x", padx=10, pady=(0,6))

        ttk.Button(quick, text="EN→JA (B2) 開始", command=self.quick_start_en2ja).pack(side="left")
        ttk.Button(quick, text="JA→EN (B3) 開始", command=self.quick_start_ja2en).pack(side="left", padx=(8,0))

        # 文字起こし 3ボタン
        ttk.Button(quick, text="文字起こし(JA)", command=self.quick_start_stt_ja).pack(side="left", padx=(18,0))
        ttk.Button(quick, text="文字起こし(EN)", command=self.quick_start_stt_en).pack(side="left", padx=(8,0))
        ttk.Button(quick, text="文字起こし(AUTO)", command=self.quick_start_stt_auto).pack(side="left", padx=(8,0))

        ttk.Button(quick, text="すべて停止", command=self.quick_stop_all).pack(side="left", padx=(18,0))

        # Start/Stop (manual)
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=(0,8))
        ttk.Button(bar, text="Start", command=self.on_start).pack(side="left")
        ttk.Button(bar, text="Stop", command=self.on_stop).pack(side="left", padx=(8,0))

        # Log viewer
        self.txt = tk.Text(self, height=20, wrap="word")
        self.txt.pack(fill="both", expand=True, padx=10, pady=(0,10))
        self.txt.configure(font=("Consolas", 10))
        self.after(50, self.poll_log)

        self.on_direction()

    def append_log(self, s: str):
        self.txt.insert("end", s)
        self.txt.see("end")

    def poll_log(self):
        try:
            while True:
                s = log_q.get_nowait()
                self.append_log(s)
        except queue.Empty:
            pass
        self.after(80, self.poll_log)

    def on_direction(self):
        d = self.direction.get()
        # translate時は入力名をそれっぽく寄せる
        if d == "en2ja" and self.input_name.get().strip() in ("", "B3"):
            self.input_name.set("B2")
        elif d == "ja2en" and self.input_name.get().strip() in ("", "B2"):
            self.input_name.set("B3")

        # translate ja2en は language hint を ja に寄せる
        if d == "ja2en" and self.language.get().strip() == "":
            self.language.set("ja")
        if d == "en2ja" and self.language.get().strip() == "ja":
            self.language.set("")

    def build_common_params(self, include_language_hint: bool = True):
        """
        共通パラメータを組む。
        include_language_hint=True  -> 翻訳用 Language hint を --language で渡す
        include_language_hint=False -> STTのときなど、翻訳用ヒントを渡さない
        """
        p = []
        p += ["--model", self.model.get()]

        # input
        if self.device_mode.get() == "index":
            idx = self.input_index.get().strip()
            if idx.isdigit():
                p += ["--input-device", idx]
            else:
                messagebox.showwarning("Device", "Device mode is index but no valid number is set.")
        else:
            name = self.input_name.get().strip()
            if name:
                p += ["--input-name", name]

        # language hint（翻訳用）
        if include_language_hint and self.language.get().strip():
            p += ["--language", self.language.get().strip()]

        # timing
        try:
            p += ["--block-sec", str(float(self.block_sec.get()))]
        except Exception:
            p += ["--block-sec", "2.6"]
        try:
            p += ["--min-interval", str(float(self.min_interval.get()))]
        except Exception:
            p += ["--min-interval", "0.5"]

        # compute -> main.pyへは --device で渡す（autoなら渡さない）
        if self.compute.get() == "cuda":
            p += ["--device", "cuda"]
        elif self.compute.get() == "cpu":
            p += ["--device", "cpu"]

        return p

    def compute_env(self):
        mode = self.compute.get()
        env = {}
        if mode == "cpu":
            env["CUDA_VISIBLE_DEVICES"] = "-1"
        return env

    def list_devices(self):
        try:
            cmd = [VENV_PY, "-X", "utf8", MAIN_PY, "--list-devices"]
            out = subprocess.check_output(cmd, cwd=SCRIPTS_DIR, stderr=subprocess.STDOUT)
            self.append_log("\n[Devices]\n" + out.decode(errors="ignore") + "\n")
        except subprocess.CalledProcessError as e:
            self.append_log("\n[Devices] error: " + e.output.decode(errors="ignore") + "\n")
        except Exception as e:
            self.append_log(f"\n[Devices] failed: {e}\n")

    def launch(self, params, stt_lang_saved: str = None):
        """
        params で main.py を起動する。
        stt_lang_saved を渡した場合、configに最後のSTT言語を保存する（見返し用）。
        """
        cfg = {
            "direction": self.direction.get(),
            "model": self.model.get(),
            "input_name": self.input_name.get(),
            "input_index": self.input_index.get(),
            "language": self.language.get(),
            "speak": self.speak.get(),
            "voice": self.voice.get(),
            "block_sec": float(self.block_sec.get()),
            "min_interval": float(self.min_interval.get()),
            "device_mode": self.device_mode.get(),
            "compute": self.compute.get(),
            "caption": self.caption.get(),
        }
        if stt_lang_saved is not None:
            cfg["stt_language_last"] = stt_lang_saved
        save_config(cfg)

        self.append_log(f"[CMD] {VENV_PY} -X utf8 {MAIN_PY} {' '.join(params)}\n")
        env = self.compute_env()
        if "CUDA_VISIBLE_DEVICES" in env:
            self.append_log(f"[INFO] CUDA_VISIBLE_DEVICES={env['CUDA_VISIBLE_DEVICES']}\n")

        th = threading.Thread(target=run_main_py, args=(params, env), daemon=True)
        th.start()

    # ===== Buttons =====
    def quick_start_en2ja(self):
        # translate mode
        self.direction.set("en2ja")
        self.on_direction()
        params = ["--mode", "translate", "--direction", "en2ja"] + self.build_common_params(include_language_hint=True)
        if self.caption.get():
            params += ["--caption", self.caption.get()]
        if self.speak.get():
            params += ["--speak", "--voice", self.voice.get().strip() or "alloy"]
        self.launch(params)

    def quick_start_ja2en(self):
        self.direction.set("ja2en")
        self.on_direction()
        params = ["--mode", "translate", "--direction", "ja2en"] + self.build_common_params(include_language_hint=True)
        if self.caption.get():
            params += ["--caption", self.caption.get()]
        if self.speak.get():
            params += ["--speak", "--voice", self.voice.get().strip() or "alloy"]
        self.launch(params)

    # --- STT buttons (JA/EN/AUTO) ---
    def quick_start_stt_ja(self):
        # STTは翻訳方向や language hint を参照しない（事故防止）
        params = ["--mode", "stt"] + self.build_common_params(include_language_hint=False)
        params += ["--language", "ja"]  # 強制
        if self.caption.get():
            params += ["--caption", self.caption.get()]
        self.launch(params, stt_lang_saved="ja")

    def quick_start_stt_en(self):
        params = ["--mode", "stt"] + self.build_common_params(include_language_hint=False)
        params += ["--language", "en"]  # 強制
        if self.caption.get():
            params += ["--caption", self.caption.get()]
        self.launch(params, stt_lang_saved="en")

    def quick_start_stt_auto(self):
        # AUTOは --language を付けない（main.py互換が一番高い）
        params = ["--mode", "stt"] + self.build_common_params(include_language_hint=False)
        if self.caption.get():
            params += ["--caption", self.caption.get()]
        self.launch(params, stt_lang_saved="auto")

    def quick_stop_all(self):
        stop_process()

    # manual
    def on_start(self):
        # manual start = current direction translate
        params = ["--mode", "translate", "--direction", self.direction.get()] + self.build_common_params(include_language_hint=True)
        if self.caption.get():
            params += ["--caption", self.caption.get()]
        if self.speak.get():
            params += ["--speak", "--voice", self.voice.get().strip() or "alloy"]
        self.launch(params)

    def on_stop(self):
        stop_process()

if __name__ == "__main__":
    App().mainloop()

