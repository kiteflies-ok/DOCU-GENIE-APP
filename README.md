# 🧞 Docu-Genie

**Transform videos into professional documents using AI.**

Upload any video tutorial, training session, or walkthrough — and Docu-Genie will automatically transcribe it, polish it with AI, and generate a beautiful PDF document complete with screenshots.

## 🎯 What It Does

1. **Transcribes** your video using OpenAI Whisper (supports 90+ languages)
2. **Humanizes** the transcript with Mistral AI — converting raw speech into professional "Step 1, Step 2" format
3. **Captures screenshots** at key moments 
4. **Generates a PDF** with cover page, headers, footers, and styled sections

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎥 **Video Upload** | Drag & drop or click to upload (MP4, MOV, AVI) |
| 🗣️ **90+ Languages** | English, Hindi, Spanish, French, German, Chinese, Arabic, and more |
| 🤖 **AI Transcription** | Powered by OpenAI Whisper (tiny model for speed) |
| ✍️ **AI Humanization** | Mistral-7B polishes raw speech into professional SOP format |
| � **Auto Screenshots** | Captures key frames from your video |
| 📄 **Professional PDF** | Cover page, headers, footers, styled sections |
| ⚡ **Fast Processing** | Optimized for CPU deployment |


## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python, Flask, Gunicorn |
| AI Transcription | OpenAI Whisper |
| AI Humanization | Mistral-7B (via Hugging Face Inference API) |
| Video Processing | MoviePy, FFmpeg |
| PDF Generation | FPDF, Pillow |
| Database | SQLite |
| Frontend | HTML, TailwindCSS, JavaScript |
| Deployment | Docker, Hugging Face Spaces |

## 📖 How to Use

1. **Upload your video** — Drag & drop or click the upload zone
2. **Wait for processing** — The AI transcribes, humanizes, and generates your PDF
3. **Download your SOP** — Click the download button to get your professional PDF


---

Made with ✨ by **Docu-Genie** | Powered by Whisper + Mistral AI
