# OpenAI Whisper — Speech to Text
# Models: small | medium 

import static_ffmpeg
static_ffmpeg.add_paths()

import whisper
import os
import sys

file = sys.argv[1] if len(sys.argv) > 1 else "meeting.mp4"
model_name = sys.argv[2] if len(sys.argv) > 2 else "base"

print(f"Loading model: {model_name}...")
model = whisper.load_model(model_name)

print(f"Transcribing: {file}")
result = model.transcribe(file, verbose=False)

base = os.path.splitext(file)[0]
out_file = f"{base}_timestamped.txt"

with open(out_file, "w", encoding="utf-8") as f:
    for seg in result["segments"]:
        start = int(seg["start"])
        end = int(seg["end"])
        f.write(f"[{start//60:02d}:{start%60:02d} --> {end//60:02d}:{end%60:02d}] {seg['text'].strip()}\n")

print(f"Done! Saved: {out_file}")
