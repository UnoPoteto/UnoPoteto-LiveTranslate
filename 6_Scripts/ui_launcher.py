# -*- coding: utf-8 -*-
# Whisper_2O_V2 UI Launcher
# Save to: C:\Users\ilove\Projects\Whisper_2O_V2\Scripts\ui_launcher.py
#
# 目的:
#  - main.py をGUIから起動/停止する
#  - ui_launcher_config.json に設定を保存/復元
#  - EN→JA（B2）/ JA→EN（B3またはMic）をクイック起動
#  - TX/RX をトグル（アイコンボタン）で切替
#
# 前提:
#  - V2の main.py が以下オプションに対応していること:
#      --mode translate
#      --direction en2ja|ja2en
#      --model tiny|base|small|medium
#      --input-name <name>
#      --device-mode name|index
#      --compute auto|cuda|cpu
#      --block-sec <float>
#      --min-interval <float>
#      --language <hint>
#      --speak  --voice <voice>
#      --caption dst
#      --list-devices
#
# 注意:
#  - デバイス index 固定は避け、基本は device-mode=name を推奨

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

OUTPUT_DIR = os.path.join(BASE_DIR, "output")
LOGS_DIR = os.path.join(SCRIPTS_DIR, "Logs")
CONFIG_JSON = os.path.join(SCRIPTS_DIR, "ui_launcher_config.json")

# Toggle button icon files (optional)
BTN_ON_PATH = os.path.join(SCRIPTS_DIR, "Buttons", "ptt_on.png")    # TX icon
BTN_OFF_PATH = os.path.join(SCRIPTS_DIR, "Buttons", "ptt_off.png")  # RX icon
BTN_SIZE = 56  # px

# ---- Defaults for "RX/TX Toggle" ----
# RX: Discord受信など（B2）EN->JA、文字のみ
RX_DEFAULT = {
    "direction": "en2ja",
    "model": "small",
    "device_mode": "name",
    "input_name": "B2",
    "language": "",
    "speak": False,
    "voice": "alloy",
    "block_sec": 2.6,
    "min_interval": 0.5,
    "compute": "cuda",
    "caption": "dst",
}

# TX: あなたの声（例:B3）JA->EN、必要なら音声ON
TX_DEFAULT = {
    "direction": "ja2en",
    "model": "small",
    "device_mode": "name",
    "input_name": "B3",   # ここを "Microphone" 等に変えてもOK（部分一致想定）
    "language": "ja",
    "speak": True,
    "voice": "alloy",
    "block_sec": 2.4,
    "min_interval": 0.45,
    "compute": "cuda",
    "caption": "dst",
}

# ========== Subprocess management ==========
proc = None
log_q = queue.Queue()

def _read_stream(stream, q):
    try:
        for line in iter(stream.readline, b""):
            q.put(line.decode(errors="ignore"))
    finally:
        try:
            stream.close()
        except Exception:
            pass

def _run_main_py(params):
    """Launch main.py with params."""
    global proc
    if not os.path.exists(VENV_PY):
        log_q.put(f"[ERROR] python.exe not found:\n  {VENV_PY}\n")
        return
    if not os.path.exists(MAIN_PY):
        log_q.put(f"[ERROR] main.py not found:\n  {MAIN_PY}\n")
        return

    cmd = [VENV_PY, "-X", "utf8", MAIN_PY] + params

    try:
        # CREATE_NEW_PROCESS_GROUP: stop時にPID指定で落としやすい
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

        proc = subprocess.Popen(
            cmd,
            cwd=SCRIPTS_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
            env=os.environ.copy()
        )

        t = threading.Thread(target=_read_stream, args=(proc.stdout, log_q), daemon=True)
        t.start()

        ret = proc.wait()
        log_q.put(f"\n[INFO] Process exited with code {ret}\n")
    except Exception as e:
        log_q.put(f"[ERROR] Failed to launch: {e}\n")
    finally:
        proc = None

def stop_process():
    """Stop current main.py process (if any)."""
    global proc
    p = proc
    if p is None:
        log_q.put("[INFO] No running process.\n")
        return

    try:
        if p.poll() is None:
            p.terminate()
            for _ in range(25):
                if p.poll() is not None:
                    break
                time.sleep(0.1)

        if p.poll() is None:
            # 強制停止（ツリー含める）
            subprocess.call(
                ["taskkill", "/F", "/T", "/PID", str(p.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
    except Exception as e:
        log_q.put(f"[WARN] stop error: {e}\n")
    finally:
        proc = None

# ========== Config ==========
def save_config(cfg: dict):
    try:
        with open(CONFIG_JSON, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log_q.put(f"[WARN] save_config failed: {e}\n")

def load_config() -> dict:
    if os.path.exists(CONFIG_JSON):
        try:
            with open(CONFIG_JSON, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                return cfg
        except Exception:
            pass
    # defaults: RX寄り（あなたの既定に合わせる）
    return {
        "direction": RX_DEFAULT["direction"],
        "model": RX_DEFAULT["model"],
        "input_name": RX_DEFAULT["input_name"],
        "language": RX_DEFAULT["language"],
        "speak": RX_DEFAULT["speak"],
        "voice": RX_DEFAULT["voice"],
        "block_sec": RX_DEFAULT["block_sec"],
        "min_interval": RX_DEFAULT["min_interval"],
        "device_mode": RX_DEFAULT["device_mode"],
        "compute": RX_DEFAULT["compute"],
        "caption": RX_DEFAULT["caption"],
    }

# ========== UI ==========
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Whisper_2O_V2 Launcher")
        self.minsize(940, 600)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.cfg = load_config()

        # ---------------- Top Row ----------------
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=8)

        # Direction
        ttk.Label(top, text="Direction").grid(row=0, column=0, sticky="w")
        self.direction = tk.StringVar(value=self.cfg.get("direction", "en2ja"))
        ttk.Radiobutton(top, text="EN → JA", value="en2ja", variable=self.direction, command=self.on_direction).grid(row=0, column=1, sticky="w", padx=(6, 18))
        ttk.Radiobutton(top, text="JA → EN", value="ja2en", variable=self.direction, command=self.on_direction).grid(row=0, column=2, sticky="w")

        # Model
        ttk.Label(top, text="Model").grid(row=0, column=3, sticky="e")
        self.model = tk.StringVar(value=self.cfg.get("model", "small"))
        ttk.Combobox(top, textvariable=self.model, values=["tiny", "base", "small", "medium"], width=8, state="readonly").grid(row=0, column=4, sticky="w", padx=6)

        # Compute
        ttk.Label(top, text="Compute").grid(row=0, column=5, sticky="e")
        self.compute = tk.StringVar(value=self.cfg.get("compute", "cuda"))
        ttk.Combobox(top, textvariable=self.compute, values=["auto", "cuda", "cpu"], width=8, state="readonly").grid(row=0, column=6, sticky="w", padx=(6, 0))

        # Input device
        ttk.Label(top, text="Input").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.device_mode = tk.StringVar(value=self.cfg.get("device_mode", "name"))
        self.input_name = tk.StringVar(value=self.cfg.get("input_name", "B2"))
        self.input_index = tk.StringVar(value="")  # index mode を使う場合のみ

        ttk.Radiobutton(top, text="by Name", value="name", variable=self.device_mode).grid(row=1, column=1, sticky="w", pady=(6, 0))
        ttk.Radiobutton(top, text="by Index", value="index", variable=self.device_mode).grid(row=1, column=2, sticky="w", pady=(6, 0))
        ttk.Entry(top, textvariable=self.input_name, width=30).grid(row=1, column=3, columnspan=2, sticky="we", padx=(12, 0), pady=(6, 0))
        ttk.Button(top, text="List Devices", command=self.list_devices).grid(row=1, column=5, sticky="w", padx=8, pady=(6, 0))

        # Language + TTS
        ttk.Label(top, text="Language hint (optional)").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.language = tk.StringVar(value=self.cfg.get("language", ""))
        ttk.Entry(top, textvariable=self.language, width=10).grid(row=2, column=1, sticky="w", pady=(6, 0))

        self.speak = tk.BooleanVar(value=bool(self.cfg.get("speak", False)))
        ttk.Checkbutton(top, text="Speak", variable=self.speak).grid(row=2, column=2, sticky="w", pady=(6, 0))
        ttk.Label(top, text="Voice").grid(row=2, column=3, sticky="e", pady=(6, 0))
        self.voice = tk.StringVar(value=self.cfg.get("voice", "alloy"))
        ttk.Entry(top, textvariable=self.voice, width=12).grid(row=2, column=4, sticky="w", padx=6, pady=(6, 0))

        # Timing
        ttk.Label(top, text="block-sec").grid(row=3, column=0, sticky="w", pady=(6, 0))
        self.block_sec = tk.DoubleVar(value=float(self.cfg.get("block_sec", 2.6)))
        ttk.Entry(top, textvariable=self.block_sec, width=8).grid(row=3, column=1, sticky="w", pady=(6, 0))

        ttk.Label(top, text="min-interval").grid(row=3, column=2, sticky="w", pady=(6, 0))
        self.min_interval = tk.DoubleVar(value=float(self.cfg.get("min_interval", 0.5)))
        ttk.Entry(top, textvariable=self.min_interval, width=8).grid(row=3, column=3, sticky="w", pady=(6, 0))

        # Caption
        ttk.Label(top, text="caption").grid(row=3, column=4, sticky="e", pady=(6, 0))
        self.caption = tk.StringVar(value=self.cfg.get("caption", "dst"))
        ttk.Entry(top, textvariable=self.caption, width=10).grid(row=3, column=5, sticky="w", padx=6, pady=(6, 0))

        # ---------------- Quick Buttons ----------------
        quick = ttk.Frame(self)
        quick.pack(fill="x", padx=10, pady=(0, 6))

        ttk.Button(quick, text="EN→JA（B2）開始", command=self.quick_start_en2ja).pack(side="left")
        ttk.Button(quick, text="JA→EN（B3）開始", command=self.quick_start_ja2en).pack(side="left", padx=8)
        ttk.Button(quick, text="すべて停止", command=self.on_stop).pack(side="left", padx=(24, 0))

        # ---------------- Main Buttons ----------------
        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=10, pady=(4, 6))
        ttk.Button(btns, text="▶ Start", command=self.on_start).pack(side="left")
        ttk.Button(btns, text="■ Stop", command=self.on_stop).pack(side="left", padx=8)
        ttk.Button(btns, text="Open Output", command=lambda: self.open_folder(OUTPUT_DIR)).pack(side="right", padx=8)
        ttk.Button(btns, text="Open Logs", command=lambda: self.open_folder(LOGS_DIR)).pack(side="right")

        # ---------------- Toggle Icon Bar ----------------
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=(0, 6))

        self.mode_txt = tk.StringVar(value="受信: EN→JA テキスト")
        ttk.Label(bar, textvariable=self.mode_txt).pack(side="left", padx=(0, 8))

        self.latch = False  # False=RX, True=TX

        self._img_on = self._load_img(BTN_ON_PATH)
        self._img_off = self._load_img(BTN_OFF_PATH)
        if self._img_on is None or self._img_off is None:
            self.append_log(f"[WARN] Button icons not found. Put ptt_on.png / ptt_off.png under {os.path.join(SCRIPTS_DIR,'Buttons')}\n")

        self.mode_btn = ttk.Button(bar, image=self._img_off, command=self.toggle_mode)
        self.mode_btn.pack(side="left")

        # Keyboard shortcuts (toggle)
        self.bind("<KeyPress-F8>", lambda e: self.toggle_mode())
        self.bind("<KeyPress-F9>", lambda e: self.toggle_mode())

        # ---------------- Log viewer ----------------
        self.txt = tk.Text(self, height=18, wrap="word")
        self.txt.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.txt.configure(font=("Consolas", 10))
        self.after(80, self.poll_log)

        # Hotkeys for quick buttons
        self.bind_all("<Alt-Key-1>", lambda e: self.quick_start_en2ja())
        self.bind_all("<Alt-Key-2>", lambda e: self.quick_start_ja2en())
        self.bind_all("<Alt-Key-0>", lambda e: self.on_stop())

        # Init and start RX by default
        self.on_direction()
        self.apply_profile(RX_DEFAULT)
        self.on_start()
        self.update_mode_ui()

    # ---------- Helpers ----------
    def _load_img(self, path: str):
        try:
            from PIL import Image, ImageTk
            img = Image.open(path).convert("RGBA").resize((BTN_SIZE, BTN_SIZE))
            return ImageTk.PhotoImage(img)
        except Exception:
            try:
                return tk.PhotoImage(file=path)
            except Exception:
                return None

    def append_log(self, text: str):
        self.txt.insert("end", text)
        self.txt.see("end")

    def poll_log(self):
        try:
            while True:
                line = log_q.get_nowait()
                self.append_log(line)
        except queue.Empty:
            pass
        self.after(80, self.poll_log)

    def open_folder(self, path: str):
        os.makedirs(path, exist_ok=True)
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            else:
                subprocess.Popen(["open", path])
        except Exception as e:
            self.append_log(f"[WARN] cannot open folder: {e}\n")

    # ---------- Direction logic ----------
    def on_direction(self):
        d = self.direction.get()
        # 入力の目安補助（勝手に上書きしすぎない程度）
        if d == "en2ja":
            if self.language.get().strip().lower() == "ja":
                self.language.set("")
            if self.input_name.get().strip() == "":
                self.input_name.set("B2")
        else:
            if self.language.get().strip() == "":
                self.language.set("ja")
            if self.input_name.get().strip() == "":
                self.input_name.set("B3")

    # ---------- Profiles ----------
    def apply_profile(self, prof: dict):
        self.direction.set(prof.get("direction", "en2ja"))
        self.model.set(prof.get("model", "small"))
        self.device_mode.set(prof.get("device_mode", "name"))
        self.input_name.set(prof.get("input_name", "B2"))
        self.language.set(prof.get("language", ""))
        self.speak.set(bool(prof.get("speak", False)))
        self.voice.set(prof.get("voice", "alloy"))
        self.block_sec.set(float(prof.get("block_sec", 2.6)))
        self.min_interval.set(float(prof.get("min_interval", 0.5)))
        self.compute.set(prof.get("compute", "cuda"))
        self.caption.set(prof.get("caption", "dst"))

        self.on_direction()

    def update_mode_ui(self):
        if self.latch:
            self.mode_txt.set("発信: JA→EN + 音声")
            if self._img_on:
                self.mode_btn.config(image=self._img_on)
        else:
            self.mode_txt.set("受信: EN→JA テキスト")
            if self._img_off:
                self.mode_btn.config(image=self._img_off)

    def toggle_mode(self):
        # debounce
        now = time.time()
        if getattr(self, "_last_toggle", 0) and now - self._last_toggle < 0.25:
            return
        self._last_toggle = now

        self.latch = not self.latch
        self.on_stop()

        if self.latch:
            self.apply_profile(TX_DEFAULT)
        else:
            self.apply_profile(RX_DEFAULT)

        self.on_start()
        self.update_mode_ui()

    # ---------- Build params ----------
    def build_params(self):
        params = []
        params += ["--mode", "translate"]
        params += ["--direction", self.direction.get()]
        params += ["--model", self.model.get()]

        # device selection
        dm = self.device_mode.get()
        if dm == "index":
            idx = self.input_index.get().strip()
            if idx.isdigit():
                params += ["--device-mode", "index"]
                params += ["--input-name", idx]  # indexを受ける実装の場合（非推奨）
            else:
                messagebox.showwarning("Device", "Device mode is index but no valid number is set.")
                raise ValueError("invalid input index")
        else:
            name = self.input_name.get().strip()
            if not name:
                messagebox.showwarning("Device", "Input name is empty.")
                raise ValueError("empty input name")
            params += ["--device-mode", "name"]
            params += ["--input-name", name]

        lang = self.language.get().strip()
        if lang:
            params += ["--language", lang]

        # timing
        try:
            params += ["--block-sec", str(float(self.block_sec.get()))]
        except Exception:
            params += ["--block-sec", "2.6"]

        try:
            params += ["--min-interval", str(float(self.min_interval.get()))]
        except Exception:
            params += ["--min-interval", "0.5"]

        # compute
        comp = self.compute.get().strip().lower()
        if comp in ("auto", "cuda", "cpu"):
            params += ["--compute", comp]

        # speak
        if self.speak.get():
            v = (self.voice.get().strip() or "alloy")
            params += ["--speak", "--voice", v]

        # caption
        cap = self.caption.get().strip()
        if cap:
            params += ["--caption", cap]

        return params

    # ---------- Actions ----------
    def on_start(self):
        global proc
        if proc is not None:
            messagebox.showinfo("Running", "Already running.")
            return

        # save config
        cfg = {
            "direction": self.direction.get(),
            "model": self.model.get(),
            "input_name": self.input_name.get(),
            "language": self.language.get(),
            "speak": bool(self.speak.get()),
            "voice": self.voice.get(),
            "block_sec": float(self.block_sec.get()),
            "min_interval": float(self.min_interval.get()),
            "device_mode": self.device_mode.get(),
            "compute": self.compute.get(),
            "caption": self.caption.get(),
        }
        save_config(cfg)

        try:
            params = self.build_params()
        except Exception:
            return

        self.append_log(f"[CMD] {VENV_PY} -X utf8 {MAIN_PY} {' '.join(params)}\n")

        th = threading.Thread(target=_run_main_py, args=(params,), daemon=True)
        th.start()

    def on_stop(self):
        stop_process()

    def list_devices(self):
        if not os.path.exists(VENV_PY) or not os.path.exists(MAIN_PY):
            self.append_log("[ERROR] python.exe or main.py not found.\n")
            return

        try:
            cmd = [VENV_PY, "-X", "utf8", MAIN_PY, "--list-devices"]
            out = subprocess.check_output(cmd, cwd=SCRIPTS_DIR, stderr=subprocess.STDOUT)
            self.append_log("\n[Devices]\n" + out.decode(errors="ignore") + "\n")
        except subprocess.CalledProcessError as e:
            self.append_log("\n[Devices] error:\n" + e.output.decode(errors="ignore") + "\n")
        except Exception as e:
            self.append_log(f"\n[Devices] failed: {e}\n")

    def quick_start_en2ja(self):
        self.on_stop()
        self.apply_profile(RX_DEFAULT)
        self.latch = False
        self.on_start()
        self.update_mode_ui()

    def quick_start_ja2en(self):
        self.on_stop()
        self.apply_profile(TX_DEFAULT)
        self.latch = True
        self.on_start()
        self.update_mode_ui()

    def on_close(self):
        if proc is not None and messagebox.askyesno("Exit", "Stop running process?"):
            stop_process()
        self.destroy()

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)
    app = App()
    app.mainloop()

