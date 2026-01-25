# 🧞 Docu-Genie

Transform videos into PDF documentation using AI transcription.

## ✨ Features

🎥 Video upload with drag and drop  
🗣️ Supports 90+ languages including Hindi and English  
🤖 Powered by OpenAI Whisper AI  
📄 Automatic PDF generation  
🎨 Beautiful animated UI  
🚀 One-click deployment  

## 🛠️ Tech Stack

Python • Flask • Whisper • MoviePy • FPDF • SQLite • TailwindCSS

## � Installation

```bash
git clone https://github.com/kiteflies-ok/AI-POWERED-SOP.git
cd AI-POWERED-SOP
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000

## 🐳 Docker

```bash
docker build -t docu-genie .
docker run -p 5000:5000 docu-genie
```

## 🌐 Deploy to Render

Push to GitHub then connect on Render.com. The render.yaml handles everything automatically.

## 📖 Usage

1️⃣ Upload your video  
2️⃣ Wait 30-60 seconds for AI processing  
3️⃣ Download your PDF documentation  

## 🎯 Supported Formats

MP4 • MOV • AVI • Max 1024MB

## 🌍 Supported Languages

English • Hindi • Spanish • French • German • Chinese • Japanese • Arabic • 80+ more

## � Common Issues

**FFmpeg not found** → Restart your terminal  
**SSL error** → Already fixed in code  
**File too large** → Use videos under 100MB  

## 📝 License

MIT License

---

Made with ✨ by Docu-Genie
