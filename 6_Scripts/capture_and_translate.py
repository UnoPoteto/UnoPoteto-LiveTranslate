# Whisper_2O_V2 capture_and_translate.py
# Capture N seconds from device -> feed to main.py --input-file
# Supports:
#   --mode translate (default) : transcribe + translate + optional TTS
#   --mode stt                 : transcribe only (+ optional caption output)

import os, sys, argparse, subprocess, datetime as dt, winsound
import numpy as np
import sounddevice as sd
import soundfile as sf

SCRIPT_DIR = os.path.dirname(__file__)
BASE_DIR   = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
AUDIO_DIR  = os.path.join(SCRIPT_DIR, "Audio")
CAPTURE_DIR = os.path.join(AUDIO_DIR, "Captures")
LOG_DIR    = os.path.join(SCRIPT_DIR, "Logs")
os.makedirs(CAPTURE_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

def find_input_device(name_keyword: str):
    if not name_keyword:
        return None, None
    key = name_keyword.lower()
    for i, d in enumerate(sd.query_devices()):
        if d.get("max_input_channels", 0) > 0 and key in d["name"].lower():
            return i, d["name"]
    return None, None

def main():
    ap = argparse.ArgumentParser("Capture N seconds from device then process via main.py")
    ap.add_argument("--input-name", required=True, help='例: "B1" / "B2" / "B3" / "Voicemeeter Out B2"')
    ap.add_argument("--duration", type=float, default=180.0, help="録音秒数 (default: 180)")
    ap.add_argument("--samplerate", type=int, default=16000)
    ap.add_argument("--channels", type=int, default=1)

    ap.add_argument("--mode", choices=["translate","stt"], default="translate")
    ap.add_argument("--direction", choices=["en2ja","ja2en"], default="en2ja")
    ap.add_argument("--model", default="small")
    ap.add_argument("--language", default=None, help="ja / en を固定したい場合に指定")

    ap.add_argument("--caption", choices=["none","src","dst","both"], default=None)
    ap.add_argument("--caption-file", default=None)

    ap.add_argument("--log", action="store_true", help="main.py 側の --log を有効化（ファイル処理ログ）")
    ap.add_argument("--speak", action="store_true")
    ap.add_argument("--voice", default="alloy")

    args = ap.parse_args()

    dev_index, dev_name = find_input_device(args.input_name)
    if dev_index is None:
        print(f'❌ 入力デバイスが見つかりません: "{args.input_name}"')
        print("  → python main.py --list-devices で名称を確認してください。")
        sys.exit(1)

    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    wav_name = f"clip_{args.mode}_{args.direction}_{ts}.wav"
    wav_path = os.path.join(CAPTURE_DIR, wav_name)

    print(f"🎚 Input = [{dev_index}] {dev_name}")
    print(f"🎙️ {args.duration:.1f} sec recording -> {wav_path}")
    winsound.MessageBeep()

    sd.default.device = (dev_index, None)
    frames = int(args.samplerate * args.duration)
    buf = sd.rec(frames, samplerate=args.samplerate, channels=args.channels, dtype="float32")
    sd.wait()
    audio = np.squeeze(buf)
    sf.write(wav_path, audio, args.samplerate)
    print("✅ 録音完了")

    # main.py を --input-file で実行（同じ venv の Python で）
    cmd = [
        sys.executable, os.path.join(SCRIPT_DIR, "main.py"),
        "--mode", args.mode,
        "--direction", args.direction,
        "--model", args.model,
        "--input-file", wav_path,
    ]
    if args.log:
        cmd += ["--log"]
    if args.language:
        cmd += ["--language", args.language]
    if args.caption is not None:
        cmd += ["--caption", args.caption]
    if args.caption_file:
        cmd += ["--caption-file", args.caption_file]
    if args.speak and args.mode != "stt":
        cmd += ["--speak", "--voice", args.voice]

    print("🧠 実行:", " ".join(f'"{c}"' if " " in c else c for c in cmd))
    try:
        subprocess.run(cmd, check=True)
    finally:
        winsound.MessageBeep()
        print("🏁 完了")

if __name__ == "__main__":
    main()

