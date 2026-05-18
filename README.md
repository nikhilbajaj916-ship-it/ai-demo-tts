# Kokoro TTS – Transcript to Synchronized Audio

## Built

A Python tool that takes a timestamped transcript and converts it into a voiceover audio file 

Each line of narration starts exactly at its timestamp — no overlap, no drift, no missing words.

---

## How It Works

1. Transcript is written with timestamps marking when each narration should begin
2. The tool reads each segment, generates natural-sounding speech using Kokoro AI
3. Silence gaps are automatically inserted between segments to maintain exact timing
4. All segments are stitched into one final audio file matching the video duration exactly

---

## Requirements

- **Python 3.9+**
- **Kokoro AI** — local TTS model, runs fully offline after initial setup
- **ffmpeg** — used only for audio format conversion (WAV to MP3)
- **Model files** — `kokoro-v0_19.onnx` and `voices.bin` (place in project folder)

## Ideal Timing Design

Each segment follows this logic:
```
**This project used ~209 WPM** (760 words in 3:38 min) — achieved by forcing Kokoro to speed=1.6x.

Timestamp starts → silence fills gap → narration plays → next timestamp starts
```
- If narration finishes early → silence holds until next timestamp
- If narration runs slightly long → next segment starts immediately after (no overlap)
- Final audio is exactly **3 minutes 38 seconds** — padded with silence if short, trimmed if over.

---

## Output

- `final_audio_kokoro.mp3` — final combined audio, exactly 3:38
- `segments/` folder — individual MP3 per segment for manual review

---

### WPM Requirement

| Use Case | WPM | Feel |
|----------|-----|------|
| Audiobook / storytelling | 120–140 | Relaxed |
| Professional narration / demo | **140–160** | Clear
| Fast-paced tech demo | 160–180 | Energetic but still clear |
| Above 180 | Too fast | Hard to follow |

**Target: 150 WPM** — this is the sweet spot for a product demo. Sounds confident, not rushed.

---

### Ideal Words Per Second on Screen

At 150 WPM → **2.5 words per second**

Use this to plan how many words to write per segment:

| Screen stays for | Max words to write |
|------------------|--------------------|
| 3 seconds | 7 words |
| 5 seconds | 12 words |
| 7 seconds | 17 words |
| 10 seconds | 25 words |
| 15 seconds | 37 words |


