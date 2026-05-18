import os
os.environ["PATH"] = r"C:\Users\nikhi\Downloads\ffmpeg-8.1-essentials_build\ffmpeg-8.1-essentials_build\bin" + os.pathsep + os.environ.get("PATH", "")

import soundfile as sf
from pydub import AudioSegment
from kokoro_onnx import Kokoro

kokoro = Kokoro("kokoro-v0_19.onnx", "voices.bin")
print("Kokoro loaded!\n")

text = "This Proof of Concept has been developed for SMBC USA. It showcases an Operational Control Dashboard — providing real-time updates across Finance functions, with full transparency and governance built in."

voices = [
    "af_bella",
    "af_sarah",
    "af_sky",
    "af_nicole",
    "am_adam",
    "am_michael",
]

os.makedirs("voice_demos", exist_ok=True)

for voice in voices:
    print(f"Generating: {voice}...")
    try:
        samples, sample_rate = kokoro.create(text, voice=voice, speed=1.3, lang="en-us")
        wav = f"voice_demos/{voice}.wav"
        sf.write(wav, samples, sample_rate)
        seg = AudioSegment.from_wav(wav)
        seg.export(f"voice_demos/{voice}.mp3", format="mp3")
        os.remove(wav)
        print(f"  Saved: voice_demos/{voice}.mp3 ({len(seg)/1000:.1f}s)")
    except Exception as e:
        print(f"  FAILED ({voice}): {e}")

print("\nDone! Listen to voice_demos/ folder and pick your favourite.")
