---
title: Docu-Genie
emoji: 🧞
colorFrom: purple
colorTo: blue
sdk: docker
pinned: false
---

# 🧞 Docu-Genie

**Transform videos into professional documents using AI.**

Upload any video tutorial, training session, or walkthrough — and Docu-Genie will automatically transcribe it, polish it with AI, and generate a beautiful PDF document complete with screenshots.

## 🎯 What It Does

1. **Transcribes** your video using OpenAI Whisper (supports 90+ languages)
2. **Humanizes** the transcript with Mistral AI — converting raw speech into professional "Step 1, Step 2" format
3. **Captures screenshots** at key moments (10%, 50%, 90% of video)
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

### Processing Time (Free CPU)

| Video Length | Approximate Time |
|--------------|------------------|
| 1 minute | ~1-2 minutes |
| 5 minutes | ~3-5 minutes |
| 10 minutes | ~5-8 minutes |

## 🚀 Deploy Your Own

### Hugging Face Spaces (Recommended)

1. Fork this Space or clone the repo
2. Go to Settings → Variables and Secrets
3. Add secret: `HF_TOKEN` = Your Hugging Face access token
4. Restart the Space

### Local Development

```bash
git clone https://github.com/kiteflies-ok/docu-genie-app.git
cd docu-genie-app
pip install -r requirements.txt
python app.py
```

Open http://localhost:7860

### Docker

```bash
docker build -t docu-genie .
docker run -p 7860:7860 docu-genie
```

## 🔧 Configuration

| Environment Variable | Description |
|---------------------|-------------|
| `HF_TOKEN` | Hugging Face access token (required for AI humanization) |

## 🎯 Supported Formats

- **Video**: MP4, MOV, AVI, MKV, WebM
- **Max Size**: 1GB
- **Languages**: 90+ (auto-detected)

## 📄 PDF Output Includes

- ✅ Professional cover page with title and date
- ✅ "Docu-Genie SOP" header on every page
- ✅ Page numbers (e.g., "Page 1/3")
- ✅ Screenshots at key video timestamps
- ✅ AI-polished SOP with "Step 1, Step 2" format
- ✅ Clean, readable formatting

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| **Timeout errors** | Use shorter videos (<15 min) or upgrade to GPU Space |
| **AI humanization fails** | Check that `HF_TOKEN` secret is set correctly |
| **Poor transcription** | Ensure clear audio in source video |

## 📝 License

MIT License

---

Made with ✨ by **Docu-Genie** | Powered by Whisper + Mistral AI
