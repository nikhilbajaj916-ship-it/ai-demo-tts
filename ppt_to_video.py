"""
ppt_to_video.py — Convert a PPTX + slide-wise transcript → narrated MP4

Pipeline:
  1. Parse transcript  (HH:MM:SS --> HH:MM:SS blocks, one per slide)
  2. Export PPTX slides → PNG images
       Windows with PowerPoint installed → COM automation (best quality)
       Fallback                          → LibreOffice headless
  3. Generate TTS audio per slide via Kokoro (af_sky, speed=1.1)
  4. Build silent slideshow — each slide shown for its TTS audio duration
  5. Merge audio + video → final MP4

Usage:
  python ppt_to_video.py presentation.pptx transcript.txt [output.mp4]

Transcript format (same as kokoro_zenlabs.py):
  00:00:00 --> 00:00:16
  Slide 1 narration text here.

  00:00:16 --> 00:00:30
  Slide 2 narration text here.

Requirements:
  pip install python-pptx kokoro-onnx soundfile pydub static-ffmpeg
  + Microsoft PowerPoint (Windows)  OR  LibreOffice in PATH
"""

import os
import sys
import subprocess
import re
import glob
import static_ffmpeg
static_ffmpeg.add_paths()

from pydub import AudioSegment
import soundfile as sf
from kokoro_onnx import Kokoro

# ── TTS Config ────────────────────────────────────────────────────────────────
VOICE         = "af_sky"
SPEED         = 1.1
KOKORO_MODEL  = "kokoro-v0_19.onnx"
KOKORO_VOICES = "voices.bin"

# ── Transcript Parser ─────────────────────────────────────────────────────────
def _time_to_ms(t: str) -> int:
    h, m, s = map(int, t.strip().split(":"))
    return (h * 3600 + m * 60 + s) * 1000

def parse_transcript(path: str) -> list[tuple[int, int, str]]:
    """Return list of (start_ms, end_ms, text) from HH:MM:SS --> HH:MM:SS blocks."""
    pattern = re.compile(r"(\d{2}:\d{2}:\d{2})\s*-->\s*(\d{2}:\d{2}:\d{2})")
    with open(path, encoding="utf-8") as f:
        lines = [l.rstrip() for l in f]

    entries, i = [], 0
    while i < len(lines):
        m = pattern.match(lines[i])
        if m:
            start_ms = _time_to_ms(m.group(1))
            end_ms   = _time_to_ms(m.group(2))
            i += 1
            parts = []
            while i < len(lines) and not pattern.match(lines[i]):
                if lines[i].strip():
                    parts.append(lines[i].strip())
                i += 1
            if parts:
                entries.append((start_ms, end_ms, " ".join(parts)))
        else:
            i += 1
    return entries

# ── Slide Export ──────────────────────────────────────────────────────────────
def _export_via_com(pptx_path: str, out_dir: str) -> list[str]:
    """Export every slide as PNG using PowerPoint COM (Windows + Office required)."""
    import comtypes.client

    pptx_abs = os.path.abspath(pptx_path)
    out_abs  = os.path.abspath(out_dir)
    os.makedirs(out_abs, exist_ok=True)

    ppt  = comtypes.client.CreateObject("PowerPoint.Application")
    ppt.Visible = 1
    deck = ppt.Presentations.Open(pptx_abs, ReadOnly=True, WithWindow=False)

    images = []
    for i, slide in enumerate(deck.Slides, start=1):
        img_path = os.path.join(out_abs, f"slide_{i:03d}.png")
        slide.Export(img_path, "PNG")
        images.append(img_path)

    deck.Close()
    ppt.Quit()
    return sorted(images)


def _export_via_libreoffice(pptx_path: str, out_dir: str) -> list[str]:
    """Export slides to PNG using LibreOffice headless (cross-platform fallback)."""
    os.makedirs(out_dir, exist_ok=True)
    subprocess.run(
        ["libreoffice", "--headless", "--convert-to", "png",
         "--outdir", out_dir, pptx_path],
        check=True,
    )
    base   = os.path.splitext(os.path.basename(pptx_path))[0]
    images = sorted(glob.glob(os.path.join(out_dir, f"{base}*.png")))
    return images


def export_slides(pptx_path: str, out_dir: str, method: str = "auto") -> list[str]:
    """
    Export PPTX slides to PNG images.

    method: "auto"        — try COM first, fall back to LibreOffice
            "com"         — PowerPoint COM (Windows + Office)
            "libreoffice" — LibreOffice headless
    """
    if method == "auto":
        try:
            import comtypes.client  # noqa: F401
            method = "com"
        except ImportError:
            method = "libreoffice"

    if method == "com":
        return _export_via_com(pptx_path, out_dir)
    return _export_via_libreoffice(pptx_path, out_dir)

# ── TTS Generator ─────────────────────────────────────────────────────────────
def _clean_text(text: str) -> str:
    return (
        text.replace("—", ", ").replace("–", ", ")
            .replace("\u2018", "'").replace("\u2019", "'")
    )


def generate_tts(kokoro: Kokoro, text: str) -> AudioSegment:
    samples, sr = kokoro.create(_clean_text(text), voice=VOICE, speed=SPEED, lang="en-us")
    wav = "_tmp_ppt_seg.wav"
    sf.write(wav, samples, sr)
    seg = AudioSegment.from_wav(wav)
    os.remove(wav)
    return seg

# ── Video Builder ─────────────────────────────────────────────────────────────
def build_slideshow(images: list[str], durations_ms: list[int], out_path: str):
    """
    Create a video where each image is shown for its audio duration.
    Uses ffmpeg concat demuxer for frame-accurate timing.
    """
    list_path = "_ppt_slide_list.txt"
    with open(list_path, "w") as f:
        for img, dur_ms in zip(images, durations_ms):
            f.write(f"file '{os.path.abspath(img)}'\n")
            f.write(f"duration {dur_ms / 1000:.3f}\n")
        # ffmpeg concat requires repeating the last entry without duration
        f.write(f"file '{os.path.abspath(images[-1])}'\n")

    cmd = [
        "ffmpeg",
        "-f", "concat", "-safe", "0", "-i", list_path,
        "-vf", (
            "scale=1920:1080:force_original_aspect_ratio=decrease,"
            "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black"
        ),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-y", out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    os.remove(list_path)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg slideshow error:\n{result.stderr[-800:]}")


def merge_audio_video(video_path: str, audio_path: str, out_path: str):
    """Mux audio track into video file."""
    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-map", "0:v:0", "-map", "1:a:0",
        "-shortest", "-y", out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg merge error:\n{result.stderr[-800:]}")

# ── Main Function ─────────────────────────────────────────────────────────────
def ppt_to_video(
    pptx_path: str,
    transcript_path: str,
    output_path: str = None,
    slide_export: str = "auto",   # "auto" | "com" | "libreoffice"
    log=print,
) -> str | None:
    """
    Full pipeline: PPTX + transcript → narrated MP4.

    Returns output_path on success, None on failure.
    """
    output_path = output_path or os.path.splitext(pptx_path)[0] + "_narrated.mp4"
    slides_dir  = "_ppt_slide_exports"

    # 1. Parse transcript
    log("Parsing transcript...")
    entries = parse_transcript(transcript_path)
    if not entries:
        log("ERROR: No transcript segments found.")
        return None
    log(f"  {len(entries)} segments found.")

    # 2. Export slides
    log(f"Exporting slides ({slide_export})...")
    try:
        images = export_slides(pptx_path, slides_dir, method=slide_export)
    except Exception as e:
        log(f"ERROR exporting slides: {e}")
        return None
    log(f"  {len(images)} slides exported → {slides_dir}/")

    # Align counts — warn if mismatched
    if len(images) != len(entries):
        log(f"WARNING: {len(images)} slides vs {len(entries)} transcript segments — using minimum.")
        n       = min(len(images), len(entries))
        images  = images[:n]
        entries = entries[:n]

    # 3. Generate TTS per slide
    log("Loading Kokoro TTS model...")
    kokoro     = Kokoro(KOKORO_MODEL, KOKORO_VOICES)
    full_audio = AudioSegment.silent(duration=0)
    durations  = []

    for idx, (start_ms, end_ms, text) in enumerate(entries):
        window_ms = end_ms - start_ms
        log(f"\n  [{idx+1}/{len(entries)}] {start_ms//1000}s → {end_ms//1000}s")
        log(f"   Text: {text[:70]}{'...' if len(text)>70 else ''}")
        try:
            seg = generate_tts(kokoro, text)
            log(f"   TTS: {len(seg)/1000:.1f}s  (window: {window_ms/1000:.0f}s)")
        except Exception as e:
            log(f"   TTS FAILED: {e} — using silence for window duration")
            seg = AudioSegment.silent(duration=window_ms)

        full_audio += seg
        durations.append(len(seg))

    audio_tmp = "_ppt_narration.mp3"
    full_audio.export(audio_tmp, format="mp3")
    total_s = len(full_audio) / 1000
    log(f"\nFull audio: {int(total_s//60)}m {int(total_s%60)}s → {audio_tmp}")

    # 4. Build silent slideshow timed to TTS durations
    log("Building slideshow video...")
    video_tmp = "_ppt_video_raw.mp4"
    try:
        build_slideshow(images, durations, video_tmp)
    except RuntimeError as e:
        log(f"ERROR: {e}")
        return None
    log(f"  Slideshow video: {video_tmp}")

    # 5. Merge audio + video
    log("Merging audio into video...")
    try:
        merge_audio_video(video_tmp, audio_tmp, output_path)
    except RuntimeError as e:
        log(f"ERROR: {e}")
        return None

    # Cleanup temp files
    for f in [audio_tmp, video_tmp]:
        if os.path.exists(f):
            os.remove(f)

    log(f"\nDone! Output: {output_path}")
    return output_path


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python ppt_to_video.py <presentation.pptx> <transcript.txt> [output.mp4]")
        sys.exit(1)

    pptx       = sys.argv[1]
    transcript = sys.argv[2]
    out        = sys.argv[3] if len(sys.argv) > 3 else None

    result = ppt_to_video(pptx, transcript, out)
    sys.exit(0 if result else 1)
