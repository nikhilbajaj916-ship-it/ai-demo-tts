import subprocess
import static_ffmpeg
static_ffmpeg.add_paths()

input_file = r"C:\Users\nikhi\Pictures\tts\input.mov"   # apni MOV file ka path yahan dalo
output_file = r"C:\Users\nikhi\Pictures\tts\output.mp4"

subprocess.run([
    "ffmpeg", "-i", input_file,
    "-c:v", "copy", "-c:a", "aac",
    output_file
])

print("Done!")
