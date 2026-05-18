import os
import re
import sys
os.environ["PATH"] = r"C:\Users\nikhi\Downloads\ffmpeg-8.1-essentials_build\ffmpeg-8.1-essentials_build\bin" + os.pathsep + os.environ.get("PATH", "")

from pydub import AudioSegment
import soundfile as sf
from kokoro_onnx import Kokoro

kokoro = Kokoro("kokoro-v0_19.onnx", "voices.bin")

VOICE = "af_sky"
SPEED = 1.1

def time_to_ms(t):
    h, m, s = map(int, t.strip().split(':'))
    return (h * 3600 + m * 60 + s) * 1000

def parse_timestamp_line(line):
    match = re.match(r'(\d{2}:\d{2}:\d{2})\s*-->\s*(\d{2}:\d{2}:\d{2})', line)
    if match:
        return time_to_ms(match.group(1)), time_to_ms(match.group(2))
    return None

with open("transcript_smbc.txt", "r", encoding="utf-8") as f:
    lines = [line.rstrip() for line in f.readlines()]

entries = []
i = 0
while i < len(lines):
    ts = parse_timestamp_line(lines[i])
    if ts:
        start_ms, end_ms = ts
        text_parts = []
        i += 1
        while i < len(lines) and not parse_timestamp_line(lines[i]):
            if lines[i].strip():
                text_parts.append(lines[i].strip())
            i += 1
        if text_parts:
            entries.append((start_ms, end_ms, " ".join(text_parts)))
    else:
        i += 1

# Get segment number from argument (1-based), default to 1
seg_num = int(sys.argv[1]) if len(sys.argv) > 1 else 1
idx = seg_num - 1

if idx < 0 or idx >= len(entries):
    print(f"Segment {seg_num} not found. Total segments: {len(entries)}")
    sys.exit(1)

start_ms, end_ms, text = entries[idx]
window_ms = end_ms - start_ms
clean_text = text.replace("—", ", ").replace("–", ", ").replace("'", "'").replace("'", "'")

print(f"\nSeg {seg_num} | {start_ms//1000}s → {end_ms//1000}s | window: {window_ms/1000:.0f}s")
print(f"Words: {len(clean_text.split())} | Max at {SPEED}x: {int(window_ms/1000 * 152 / 60)} words")
print(f"Text: {clean_text}")

samples, sample_rate = kokoro.create(clean_text, voice=VOICE, speed=SPEED, lang="en-us")
wav_file = "temp_seg.wav"
sf.write(wav_file, samples, sample_rate)
seg = AudioSegment.from_wav(wav_file)
os.remove(wav_file)

out_file = f"seg_{seg_num:02d}_preview.mp3"
seg.export(out_file, format="mp3")
print(f"\nDuration: {len(seg)/1000:.1f}s | Window: {window_ms/1000:.0f}s")
print(f"Saved: {out_file}")
