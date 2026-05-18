import os
import re
import time
os.environ["PATH"] = r"C:\Users\nikhi\Downloads\ffmpeg-8.1-essentials_build\ffmpeg-8.1-essentials_build\bin" + os.pathsep + os.environ.get("PATH", "")

from pydub import AudioSegment
import soundfile as sf
from kokoro_onnx import Kokoro

kokoro = Kokoro("kokoro-v0_19.onnx", "voices.bin")
print("Kokoro loaded!\n")

VOICE = "af_sky"
SPEED = 1.1
GAP_SCALE = 0.83  # reduce inter-segment gaps to shorten total duration (1.0 = full gaps)

# ── Helpers ──────────────────────────────────────────────────────────────────
def time_to_ms(t):
    t = t.strip().replace(',', '.')
    parts = t.split(':')
    h, m, s = int(parts[0]), int(parts[1]), float(parts[2])
    return int((h * 3600 + m * 60 + s) * 1000)

def parse_timestamp_line(line):
    match = re.match(r'(\d{2}:\d{2}:\d{2}[,\.]\d+)\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d+)', line)
    if not match:
        match = re.match(r'(\d{2}:\d{2}:\d{2})\s*-->\s*(\d{2}:\d{2}:\d{2})', line)
    if match:
        return time_to_ms(match.group(1)), time_to_ms(match.group(2))
    return None

def generate_audio(text, speed=SPEED):
    samples, sample_rate = kokoro.create(text, voice=VOICE, speed=speed, lang="en-us")
    wav_file = "temp_seg.wav"
    sf.write(wav_file, samples, sample_rate)
    seg = AudioSegment.from_wav(wav_file)
    os.remove(wav_file)
    return seg

# ── Parse transcript ─────────────────────────────────────────────────────────
with open("new_file.srt", "r", encoding="utf-8") as f:
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
            text = " ".join(text_parts)
            entries.append((start_ms, end_ms, text))
    else:
        i += 1

print(f"Total segments: {len(entries)}\n")

# ── Generate TTS — fit each segment to exact window ──────────────────────────
os.makedirs("segments_zenlabs_sky", exist_ok=True)

final_audio = AudioSegment.silent(duration=0)
current_ms = 0

for idx, (start_ms, end_ms, text) in enumerate(entries):
    window_ms = end_ms - start_ms
    clean_text = text.replace("—", ", ").replace("–", ", ").replace("\u2018", "'").replace("\u2019", "'")

    print(f"\n[{idx+1}/{len(entries)}] {start_ms//1000}s -> {end_ms//1000}s (window: {window_ms/1000:.0f}s)")
    print(f"  Words: {len(clean_text.split())} | Text: {clean_text[:60]}...")

    # Add silence for the gap before this segment (scaled to control total duration)
    if start_ms > current_ms:
        gap_ms = int((start_ms - current_ms) * GAP_SCALE)
        final_audio += AudioSegment.silent(duration=gap_ms)
        current_ms = start_ms

    try:
        seg = generate_audio(clean_text, SPEED)
        print(f"  Duration: {len(seg)/1000:.1f}s | Window: {window_ms/1000:.0f}s")

        seg.export(f"segments_zenlabs_sky/seg_{idx+1:02d}_{start_ms//1000:04d}ms.mp3", format="mp3")

        final_audio += seg
        current_ms += len(seg)

    except Exception as e:
        print(f"  FAILED: {e}")
        current_ms += window_ms

    time.sleep(0.2)

final_audio.export("final_audio_zenlabs_sky.mp3", format="mp3")
mins = len(final_audio) // 60000
secs = (len(final_audio) % 60000) // 1000
print(f"\nDone! final_audio_zenlabs_sky.mp3 — {mins}:{secs:02d}")

# ── Background music options (for Streamlit dropdown) ────────────────────────
BG_MUSIC_OPTIONS = {
    "None"              : None,
    "Corporate"         : "music/atlasaudio-corporate-491319.mp3",
    "Upbeat Corporate"  : "music/kornevmusic-upbeat-happy-corporate-487426.mp3",
    "Soft Background"   : "music/sigmamusicart-soft-background-music-468495.mp3",
    "Background"        : "music/background.mp3.mp3",
}

# ── Active background music — change here or via Streamlit dropdown ───────────
BG_MUSIC  = BG_MUSIC_OPTIONS["None"]   # set to any key above to enable
BG_VOLUME = -30                         # dB reduction (more negative = quieter)

if BG_MUSIC and os.path.exists(BG_MUSIC):
    print(f"\nMixing background music: {BG_MUSIC}")
    bg = AudioSegment.from_mp3(BG_MUSIC)
    bg = bg - abs(BG_VOLUME)
    if len(bg) < len(final_audio):
        loops = len(final_audio) // len(bg) + 1
        bg = bg * loops
    bg = bg[:len(final_audio)]
    mixed = final_audio.overlay(bg)
    mixed.export("final_audio_with_music.mp3", format="mp3")
    print("Done! final_audio_with_music.mp3")
elif BG_MUSIC:
    print(f"\nMusic file not found ({BG_MUSIC}) — skipping mix.")
else:
    print("\nNo background music selected.")
