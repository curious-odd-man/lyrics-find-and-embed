import whisperx

# Load and transcribe
model = whisperx.load_model("large-v2", device="cpu")
audio = whisperx.load_audio(r"C:\Users\curious\Desktop\01 Mamma Mia.m4a")
result = model.transcribe(audio)

# Align for word-level timestamps
model_a, metadata = whisperx.load_align_model(language_code=result["language"], device="gpu")
result = whisperx.align(result["segments"], model_a, metadata, audio, device="gpu")

# Output word timestamps
for segment in result["segments"]:
    for word in segment["words"]:
        print(f"{word['start']:.3f} --> {word['end']:.3f}  {word['word']}")