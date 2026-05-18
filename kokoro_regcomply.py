import os
import re
import time
os.environ["PATH"] = r"C:\Users\nikhi\Downloads\ffmpeg-8.1-essentials_build\ffmpeg-8.1-essentials_build\bin" + os.pathsep + os.environ.get("PATH", "")

from pydub import AudioSegment
import soundfile as sf

from kokoro_onnx import Kokoro
kokoro = Kokoro("kokoro-v0_19.onnx", "voices.bin")
print("Kokoro loaded!\n")

# ── Helpers ──────────────────────────────────────────────────────────────────
def is_timestamp(s):
    return bool(re.match(r'^\d{2}:\d{2}:\d{2}$', s))

def time_to_ms(t):
    h, m, s = map(int, t.split(':'))
    return (h * 3600 + m * 60 + s) * 1000

def fit_to_duration(seg, target_ms):
    # No post-processing — Kokoro speed=1.13 handles timing natively
    if len(seg) > target_ms:
        print(f"  Overflow: {len(seg)/1000:.1f}s > {target_ms/1000:.0f}s — playing naturally")
    return seg

# ── Parse transcript ─────────────────────────────────────────────────────────
with open("transcript_regcomply.txt", "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f.readlines() if line.strip()]

entries = []
i = 0
while i < len(lines):
    if is_timestamp(lines[i]):
        timestamp = lines[i]
        text_parts = []
        i += 1
        while i < len(lines) and not is_timestamp(lines[i]):
            text_parts.append(lines[i])
            i += 1
        if text_parts:
            entries.append((timestamp, " ".join(text_parts)))
    else:
        i += 1

print(f"Total segments: {len(entries)}")

# ── Target durations ─────────────────────────────────────────────────────────
TOTAL_DURATION_MS = 3 * 60 * 1000 + 24 * 1000  # 3:24 = 204000ms
LAST_SEG_DURATION_MS = 30 * 1000                # last segment buffer = 30s

timestamps_ms = [time_to_ms(e[0]) for e in entries]
target_durations = []
for i in range(len(timestamps_ms)):
    if i + 1 < len(timestamps_ms):
        duration = timestamps_ms[i + 1] - timestamps_ms[i]
    else:
        duration = LAST_SEG_DURATION_MS
    target_durations.append(duration)

# ── Generate TTS ─────────────────────────────────────────────────────────────
os.makedirs("segments_regcomply", exist_ok=True)

final_audio = AudioSegment.silent(duration=0)
current_ms = 0

for idx, ((time_line, text_line), target_ms) in enumerate(zip(entries, target_durations)):
    clean_text = text_line.replace("—", ", ").replace("–", ", ").replace("'", "'").replace("'", "'")
    start_ms = time_to_ms(time_line)
    print(f"\n[{idx+1}/{len(entries)}] {time_line} | gap: {target_ms/1000:.0f}s")
    print(f"  Text: {clean_text[:70]}...")

    # Insert silence to reach timestamp
    if start_ms > current_ms:
        final_audio += AudioSegment.silent(duration=start_ms - current_ms)
        current_ms = start_ms

    try:
        samples, sample_rate = kokoro.create(
            clean_text,
            voice="af_bella",
            speed=1.13,
            lang="en-us"
        )

        wav_file = f"temp_seg_{idx}.wav"
        sf.write(wav_file, samples, sample_rate)
        seg = AudioSegment.from_wav(wav_file)
        os.remove(wav_file)

        print(f"  TTS: {len(seg)/1000:.1f}s | target: {target_ms/1000:.0f}s")
        seg = fit_to_duration(seg, target_ms)

        seg.export(f"segments_regcomply/seg_{idx+1:02d}_{time_line.replace(':', '-')}.mp3", format="mp3")

        final_audio += seg
        current_ms += len(seg)
        print(f"  ✅ Placed at {start_ms/1000:.0f}s")

    except Exception as e:
        print(f"  FAILED: {e}")
        final_audio += AudioSegment.silent(duration=target_ms)
        current_ms += target_ms

    time.sleep(0.2)

# Pad if shorter, never trim — last segment must finish completely
if len(final_audio) < TOTAL_DURATION_MS:
    final_audio += AudioSegment.silent(duration=TOTAL_DURATION_MS - len(final_audio))

final_audio.export("final_audio_regcomply.mp3", format="mp3")
mins = len(final_audio) // 60000
secs = (len(final_audio) % 60000) // 1000
print(f"\n✅ Done! final_audio_regcomply.mp3 — {mins}:{secs:02d}")
