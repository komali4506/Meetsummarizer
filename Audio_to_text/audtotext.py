import whisper

# Transcribe audio
audio_path = "audio_output.mp3"
model = whisper.load_model("base")
print("🔁 Transcribing...")
result = model.transcribe(audio_path)
transcribed_text = result["text"]

# Save transcription to TXT
txt_path = "transcription_output.txt"
with open(txt_path, "w", encoding="utf-8") as f:
    f.write(transcribed_text)

print(f"✅ Transcription saved as TXT: {txt_path}")
