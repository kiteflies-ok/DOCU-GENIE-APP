import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import os
import sqlite3
import uuid
from flask import Flask, render_template, request, jsonify, send_from_directory, abort
from werkzeug.utils import secure_filename
from moviepy import VideoFileClip
import whisper
from fpdf import FPDF

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 100MB limit example

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'File is too large (Max 1024MB)'}), 413

@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({'error': 'Internal Server Error'}), 500


# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# FIX: Add ffmpeg to PATH for Whisper and MoviePy
try:
    import imageio_ffmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffmpeg_dir = os.path.dirname(ffmpeg_exe)
    
    # Prepend to PATH (more reliable than appending)
    os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
    
    # Set multiple environment variables for maximum compatibility
    os.environ["FFMPEG_BINARY"] = ffmpeg_exe
    os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_exe
    
    print(f"✓ FFmpeg configured: {ffmpeg_exe}")
except ImportError:
    print("⚠ Warning: imageio_ffmpeg not found")
except Exception as e:
    print(f"⚠ Warning: Could not configure FFmpeg: {e}")


# Database setup
DB_FILE = 'database.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS jobs
                 (id TEXT PRIMARY KEY, filename TEXT, status TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# Load Whisper model (do this once at startup or lazy load)
# Using 'base' model as requested
try:
    model = whisper.load_model("base")
except Exception as e:
    print(f"Error loading Whisper model: {e}")
    model = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file part'}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        job_id = str(uuid.uuid4())
        unique_filename = f"{job_id}_{filename}"
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(video_path)
        
        # Insert job into DB
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO jobs (id, filename, status) VALUES (?, ?, ?)", (job_id, unique_filename, 'processing'))
        conn.commit()
        conn.close()
        
        try:
            # Process video
            # 1. Extract Audio
            audio_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}.wav")
            # FIX: Use VideoFileClip directly without mp. prefix
            clip = VideoFileClip(video_path)
            clip.audio.write_audiofile(audio_path, logger=None)
            clip.close()
            
            # 2. Transcribe
            if model is None:
               raise Exception("Whisper model not loaded")
            
            result = model.transcribe(audio_path)
            transcript_text = result['text']
            
            # 3. Generate PDF
            pdf_filename = f"{job_id}.pdf"
            pdf_path = os.path.join(app.config['OUTPUT_FOLDER'], pdf_filename)
            
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            
            # Handle unicode somewhat gracefully with latin-1 conversion or replacement for FPDF simple usage
            safe_text = transcript_text.encode('latin-1', 'replace').decode('latin-1')
            
            pdf.multi_cell(0, 10, safe_text)
            pdf.output(pdf_path)
            
            # Update DB
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("UPDATE jobs SET status = ? WHERE id = ?", ('completed', job_id))
            conn.commit()
            conn.close()
            
            return jsonify({
                'message': 'Processing complete',
                'download_url': f'/download/{pdf_filename}'
            })

        except Exception as e:
            print(f"Error processing job {job_id}: {e}")
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("UPDATE jobs SET status = ? WHERE id = ?", ('failed', job_id))
            conn.commit()
            conn.close()
            return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860)
