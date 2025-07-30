from transformers import pipeline

# Load the summarization model
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

# Load the transcription from TXT
with open("transcription_output.txt", "r", encoding="utf-8") as f:
    full_text = f.read()

# Break long text into chunks (model limit is ~1024 tokens)
chunks = [full_text[i:i+1000] for i in range(0, len(full_text), 1000)]

# Summarize each chunk and combine results
summary = ""
for chunk in chunks:
    result = summarizer(chunk, max_length=100, min_length=30, do_sample=False)
    summary += result[0]['summary_text'] + "\n"

# Save summary to file
with open("summary_output.txt", "w", encoding="utf-8") as f:
    f.write(summary)

print("✅ Summary saved as: summary_output.txt")
