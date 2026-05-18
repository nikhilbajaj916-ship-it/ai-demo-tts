"""
Usage:
  - Add your segments in raw_transcript.txt
  - Separate each segment with a blank line
  - Run: python format_transcript.py
  - Output: transcript_smbc.txt (formatted with timestamps)
"""

import re
from num2words import num2words

WPM = 180       # words per minute (for speed=1.2)
GAP_SEC = 2     # seconds gap between segments

def convert_numbers(text):
    text = re.sub(r'(\d+\.\d+)%', lambda m: num2words(float(m.group(1))).replace(',', '') + ' percent', text)
    text = re.sub(r'(\d+)%', lambda m: num2words(int(m.group(1))) + ' percent', text)
    text = re.sub(r'\b(\d+)\.(\d+)\b', lambda m: num2words(int(m.group(1))) + ' point ' + num2words(int(m.group(2))), text)
    text = re.sub(r'\b(\d+)\b', lambda m: num2words(int(m.group(1))), text)
    return text

with open("raw_transcript.txt", "r", encoding="utf-8") as f:
    content = f.read()

# Split into segments by ---
segments = [s.strip() for s in content.split("---") if s.strip()]
total_segs = len(segments)

print(f"{'='*45}")
print(f"  Total segments : {total_segs}")
print(f"  Speed (WPM)    : {WPM}")
print(f"  Gap between    : {GAP_SEC}s")
print(f"{'='*45}\n")

current_sec = 0
output_lines = []

for i, seg in enumerate(segments):
    # Always skip first line (heading)
    lines = seg.split("\n")
    heading = ""
    if len(lines) > 1:
        heading = lines[0].strip()
        seg = "\n".join(lines[1:]).strip()
    seg = convert_numbers(seg)
    word_count = len(seg.split())
    duration_sec = (word_count / WPM) * 60

    h = current_sec // 3600
    m = (current_sec % 3600) // 60
    s = current_sec % 60
    timestamp = f"{h:02d}:{m:02d}:{s:02d}"

    output_lines.append(timestamp)
    output_lines.append(seg)
    output_lines.append("")

    bar_filled = int((i + 1) / total_segs * 20)
    bar = "#" * bar_filled + "-" * (20 - bar_filled)
    pct = int((i + 1) / total_segs * 100)
    print(f"[{i+1}/{total_segs}] [{bar}] {pct}%")
    if heading:
        print(f"  Section  : {heading}")
    print(f"  Timestamp: {timestamp}")
    print(f"  Words    : {word_count} | Duration: {duration_sec:.0f}s")
    print()

    current_sec += int(duration_sec) + GAP_SEC

total_h = current_sec // 3600
total_m = (current_sec % 3600) // 60
total_s = current_sec % 60
print(f"{'='*45}")
print(f"  Segments processed : {total_segs}/{total_segs}")
print(f"  Estimated duration : {total_h:02d}:{total_m:02d}:{total_s:02d}")
print(f"  Transcript saved   : transcript_pay.txt")
print(f"  Audio output       : output.mp3  (run kokoro_pay.py)")
print(f"{'='*45}")

with open("transcript_pay.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))

print("Done! transcript_pay.txt ready!")
