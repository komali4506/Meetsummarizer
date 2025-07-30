# 🧠 Text Summarization using Transformers (BART)

This Python script summarizes long-form text (e.g., transcripts) using a pre-trained BART model from Hugging Face's `transformers` library.

## ✅ Features

- Uses `sshleifer/distilbart-cnn-12-6` for summarization
- Automatically splits long text into manageable chunks
- Combines summarized chunks into a final output
- Saves summary as a `.txt` file

## 📦 Requirements

Install the required Python libraries:

```bash
pip install transformers torch
pip install sentencepiece
