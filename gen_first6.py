import os
import re
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

# Only first 6 segments
entries = entries[:6]

final_audio = AudioSegment.silent(duration=0)
current_ms = 0

for idx, (start_ms, end_ms, text) in enumerate(entries):
    window_ms = end_ms - start_ms
    clean_text = text.replace("—", ", ").replace("–", ", ").replace("'", "'").replace("'", "'")

    print(f"\n[Seg {idx+1}] {start_ms//1000}s -> {end_ms//1000}s (window: {window_ms/1000:.0f}s) | {len(clean_text.split())} words")

    if start_ms > current_ms:
        final_audio += AudioSegment.silent(duration=start_ms - current_ms)
        current_ms = start_ms

    samples, sample_rate = kokoro.create(clean_text, voice=VOICE, speed=SPEED, lang="en-us")
    sf.write("temp_seg.wav", samples, sample_rate)
    seg = AudioSegment.from_wav("temp_seg.wav")
    os.remove("temp_seg.wav")

    print(f"  Audio: {len(seg)/1000:.1f}s")
    final_audio += seg
    current_ms += len(seg)

final_audio.export("preview_first6.mp3", format="mp3")
mins = len(final_audio) // 60000
secs = (len(final_audio) % 60000) // 1000
print(f"\nDone! preview_first6.mp3 — {mins}:{secs:02d}")
