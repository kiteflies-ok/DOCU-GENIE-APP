import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import os
import re
import sqlite3
import uuid
import datetime
import requests
from flask import Flask, render_template, request, jsonify, send_from_directory, abort
from werkzeug.utils import secure_filename
from moviepy import VideoFileClip
import whisper
from fpdf import FPDF
from huggingface_hub import InferenceClient
import yt_dlp

# ============================================
# AUDITOR SKILL: Structure Validator
# ============================================
class AuditorSkill:
    """
    Validates Content Repurposing Output.
    Rules:
    1. Must contain 'SECTION 1' (Executive Summary)
    2. Must contain 'SECTION 2' (Video Script)
    """
    
    def __init__(self):
        pass
    
    def run_audit(self, text):
        text_upper = text.upper()
        
        # Rule: Check for major sections
        has_sec1 = "SECTION 1" in text_upper
        has_sec2 = "SECTION 2" in text_upper
        
        if not has_sec1:
            return {
                'status': 'FAIL', 
                'reason': 'Missing SECTION 1: EXECUTIVE SUMMARY',
                'severity': 'HIGH'
            }
        
        if not has_sec2:
            return {
                'status': 'FAIL', 
                'reason': 'Missing SECTION 2: VIDEO SCRIPT',
                'severity': 'MEDIUM'
            }
            
        return {
            'status': 'PASS', 
            'reason': 'All content sections present',
            'severity': 'NONE'
        }


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['FONT_FOLDER'] = 'fonts'
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB limit

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'File is too large (Max 1024MB)'}), 413

@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({'error': 'Internal Server Error'}), 500

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
os.makedirs(app.config['FONT_FOLDER'], exist_ok=True)

# FFmpeg configuration
try:
    import imageio_ffmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffmpeg_dir = os.path.dirname(ffmpeg_exe)
    os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
    os.environ["FFMPEG_BINARY"] = ffmpeg_exe
    os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_exe
    print(f"✓ FFmpeg configured: {ffmpeg_exe}")
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

# Load Whisper
try:
    model = whisper.load_model("base")
except Exception as e:
    print(f"Error loading Whisper model: {e}")
    model = None

# Font Downloader
def download_font():
    font_path = os.path.join(app.config['FONT_FOLDER'], 'DejaVuSans.ttf')
    if not os.path.exists(font_path):
        print("Downloading unicode font...", flush=True)
        try:
            url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                with open(font_path, 'wb') as f:
                    f.write(response.content)
                print("✓ Font downloaded successfully", flush=True)
        except Exception as e:
            print(f"⚠ Font download error: {e}", flush=True)
    return font_path

FONT_PATH = download_font()


# ============================================
# CONTENT REPURPOSING AGENT
# ============================================
def generate_content_pack(raw_text, video_duration=0, target_language='English', style='Professional', cues=[]):
    """
    Generates a 3-section content pack: Summary, Script, Socials.
    """
    client = InferenceClient(model="Qwen/Qwen2.5-72B-Instruct")
    
    print(f"Generating content in {target_language} with {style} style...", flush=True)
    
    # Time cues
    duration_info = ""
    if video_duration > 0:
        cues_str = ", ".join([f"{int(c)}s" for c in cues]) if cues else "None"
        duration_info = f"Video Length: {int(video_duration)}s. Cues available at: {cues_str}."

    prompt = f"""Act as a Universal Content Analyst and Creative Director. 
You are an expert at decoding any type of video—whether it's a complex coding tutorial, a music video, a casual vlog, or a business meeting.

If the user requests {target_language}, you MUST translate the output. Do not output English unless requested.

STEP 1: ANALYZE THE GENRE
Classify the transcript into one of these categories:
- [MUSIC]: Song lyrics, abstract poetry, or music video.
- [EDUCATION]: Tutorials, 'How-To' guides, lectures, documentaries.
- [STORY]: Vlogs, travel diaries, personal stories, entertainment.
- [BUSINESS]: Meetings, calls, updates, financial reports.

STEP 2: GENERATE THE CONTENT PACK
Rewrite the transcript in a {style} tone.
Structure the output exactly into these 4 sections using the '###' delimiter for machine parsing:

### SECTION 1: THE SNAPSHOT
**Category:** [Music / Education / Story / Business]
**Title:** (Creative title adapted to the genre)
**The Hook:** (1 sentence capturing the vibe or value)
**Featured Quote:** (The most memorable line or lyric from the transcript)
**Key Takeaways:** (3 bullet points - For Songs, list 'Core Themes'; For Tutorials, list 'Learning Points'; For Business, list 'Decisions')

### SECTION 2: THE CORE CONTENT
(ADAPT THIS SECTION TO THE GENRE):
- **IF MUSIC:** Provide 'LYRIC BREAKDOWN & MEANING'. Explain the story/emotion behind the song.
- **IF EDUCATION:** Provide 'STEP-BY-STEP SCRIPT'. Use timestamps [00:00].
- **IF STORY/VLOG:** Provide 'NARRATIVE ARC'. Break it down into Beginning, Climax, and Resolution.
- **IF BUSINESS:** Provide 'MEETING MINUTES & ACTION ITEMS'.

### SECTION 3: SOCIAL MEDIA PACK
**LinkedIn:** (Professional post suited to the genre)
**Twitter:** (Thread suited to the genre - e.g., Fan thread for music, Tips for education)
**YouTube:** (SEO-optimized description with keywords)

### SECTION 4: STRATEGIC INTELLIGENCE
(ADAPT THIS SECTION TO THE GENRE):
**1. VISUALIZATION:**
- If Music/Story: Create a 'MOOD BOARD' description (Colors, Vibes, Aesthetics).
- If Education/Business: Create an ASCII FLOWCHART of the logic/process.

**2. DEEP DIVE:**
- If Music: 'HIDDEN MEANINGS' (Analyze metaphors).
- If Education: 'GAP ANALYSIS' (What was missed?).
- If Business: 'RISK ASSESSMENT'.

**3. INTERACTIVE ELEMENT:**
- If Music: 'TRIVIA QUESTION' about the artist/lyrics.
- If Education: 'KNOWLEDGE CHECK' (Quiz).
- If Business: 'DISCUSSION PROMPT'.

---
CONTEXT:
Style: {style}
Target Language: {target_language}
{duration_info}

TRANSCRIPT:
{raw_text}
"""

    messages = [{"role": "user", "content": prompt}]
    
    try:
        response = client.chat_completion(
            messages=messages,
            max_tokens=3000,
            temperature=0.7, # Higher temp for creativity
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"AI Generation Failed: {e}")
        return f"Error: {str(e)}\n\nOriginal Transcript:\n{raw_text}"


# ============================================
# PDF GENERATOR
# ============================================
class ContentPDF(FPDF):
    def __init__(self):
        super().__init__()
        font_path = os.path.join(app.config['FONT_FOLDER'], 'DejaVuSans.ttf')
        self.has_unicode = os.path.exists(font_path)
        try:
            if self.has_unicode:
                self.add_font('DejaVu', '', font_path, uni=True)
                self.main_font = 'DejaVu'
            else:
                raise Exception("Font file missing")
        except Exception as e:
            print(f"Font loading failed ({e}). Fallback to Arial.")
            self.has_unicode = False
            self.main_font = 'Arial'

    def header(self):
        if self.page_no() > 1:
            self.set_font(self.main_font, '', 10)
            self.set_text_color(150, 150, 150)
            self.set_xy(-60, 10)
            self.cell(50, 10, 'Content Pack', 0, 0, 'R')
            self.ln(15)

    def sanitize_text(self, text):
        if self.has_unicode:
            return text
        # If using Arial (Latin-1), replace common unicode chars
        replacements = {
            '\u2013': '-',   # en dash
            '\u2014': '-',   # em dash
            '\u2018': "'",   # left single quote
            '\u2019': "'",   # right single quote
            '\u201c': '"',   # left double quote
            '\u201d': '"',   # right double quote
            '\u2026': '...', # ellipsis
            '\u00a0': ' ',   # non-breaking space
        }
        for char, rep in replacements.items():
            text = text.replace(char, rep)
        # Final safety: encode/decode to strip others
        return text.encode('latin-1', 'replace').decode('latin-1')

    def chapter_title(self, title):
        self.set_font(self.main_font, '', 24)
        self.set_text_color(79, 70, 229) # Indigo
        self.cell(0, 15, self.sanitize_text(title), 0, 1, 'L')
        self.ln(5)

    def chapter_body(self, body):
        self.set_font(self.main_font, '', 11)
        self.set_text_color(50, 50, 50)
        
        # Check for ASCII Flowchart to switch to Monospace
        # New prompt uses "ASCII FLOWCHART" explicitly in instructions
        if "ASCII FLOWCHART" in body.upper() or "VISUAL FLOWCHART" in body.upper():
             # Logic to find where the chart starts/ends
             # We'll try to split by known headers or just print as is if we can't find clear boundaries
             # Simplification: If we detect it, we might just print the whole section in Monospace? 
             # No, that looks bad. Let's try to identify the block.
             
             # Heuristic: split by "2. DEEP DIVE" or similar headers from the new prompt
             parts = re.split(r'(2\.\s+DEEP\s+DIVE|THE\s+GAP\s+ANALYSIS|HIDDEN\s+MEANINGS)', body)
             
             # The flowchart is likely in parts[0]
             self.set_font("Courier", '', 10) # Monospace
             self.multi_cell(0, 7, self.sanitize_text(parts[0]))
             
             # Print the rest in normal font
             if len(parts) > 1:
                 self.set_font(self.main_font, '', 11)
                 remainder = "".join(parts[1:])
                 self.multi_cell(0, 7, self.sanitize_text(remainder))
        else:
             self.multi_cell(0, 7, self.sanitize_text(body))
        self.ln()

    def add_section_box(self, title, content):
        self.set_fill_color(245, 247, 250)
        self.rect(10, self.get_y(), 190, 8, 'F')
        self.set_font(self.main_font, '', 12)
        self.set_text_color(0, 0, 0)
        self.cell(0, 8, self.sanitize_text(title), 0, 1, 'L', True)
        self.ln(2)
        self.set_font(self.main_font, '', 10)
        self.multi_cell(0, 6, self.sanitize_text(content))
        self.multi_cell(0, 6, self.sanitize_text(content))
        self.ln(5)

def download_from_url(url):
    """Downloads video from URL using yt-dlp. Returns (job_id, video_path, filename)."""
    job_id = str(uuid.uuid4())
    
    # Configure yt-dlp to download video (for screenshots)
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_%(title)s.%(ext)s"),
        'quiet': True,
        'no_warnings': True,
        'restrictfilenames': True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Downloading from URL: {url}...", flush=True)
            info = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info)
            filename = os.path.basename(video_path)
            return job_id, video_path, filename
    except Exception as e:
        print(f"Download Error: {e}")
        raise e

# ============================================
# ROUTES
# ============================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if URL provided
    video_url = request.form.get('video_url')
    file = request.files.get('video')
    
    if not video_url and not file:
        return jsonify({'error': 'No video file or URL provided'}), 400
    
    target_language = request.form.get('language', 'English')
    style = request.form.get('style', 'Professional (Corporate)')
    screenshot_count = int(request.form.get('screenshot_count', 3))
    
    try:
        if video_url:
            job_id, video_path, filename = download_from_url(video_url)
        else:
            job_id = str(uuid.uuid4())
            filename = secure_filename(file.filename)
            video_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_{filename}")
            file.save(video_path)
            
        # Common Logic
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO jobs (id, filename, status) VALUES (?, ?, ?)", (job_id, filename, 'processing'))
        conn.commit()
        conn.close()

        temp_files = []
        auditor = AuditorSkill()
        
        # 1. Audio & Transcribe
        # 1. Audio & Transcribe
        print("Step 1: Extract/Transcribe...", flush=True)
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}.wav")
        temp_files.append(audio_path)
        
        clip = VideoFileClip(video_path)
        video_duration = clip.duration
        clip.audio.write_audiofile(audio_path, logger=None)
        
        result = model.transcribe(audio_path, fp16=False)
        raw_text = result['text']
        
        # 2. Extract Screenshots (Every 10 seconds)
        screenshots = []
        cues = []
        
        # Calculate timestamps every 10 seconds
        duration_int = int(video_duration)
        timestamps = list(range(10, duration_int, 10))
        
        # If video is shorter than 10s, take one at midpoint
        if not timestamps and duration_int > 0:
            timestamps = [duration_int // 2]
            
        for ts in timestamps:
            out_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_frame_{ts}.jpg")
            try:
                clip.save_frame(out_path, t=ts)
                screenshots.append(out_path)
                cues.append(ts)
                temp_files.append(out_path)
            except Exception as e:
                print(f"Frame extraction failed at {ts}s: {e}")
            
        clip.close()
        
        # Save Raw Transcript
        transcript_filename = f"{job_id}_transcript.txt"
        transcript_path = os.path.join(app.config['OUTPUT_FOLDER'], transcript_filename)
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(raw_text)

        # 3. Generate Content
        print("Step 2: AI Generation...", flush=True)
        generated_text = generate_content_pack(raw_text, video_duration, target_language, style, cues)
        
        # 4. Audit
        audit = auditor.run_audit(generated_text)
        print(f"Audit: {audit['status']}", flush=True)

        # 5. Parse Sections
        # Simple splitting by known headers
        sections = {
            'SECTION 1': '',
            'SECTION 2': '',
            'SECTION 3': '',
            'SECTION 4': ''
        }
        
        current_sec = None
        for line in generated_text.split('\n'):
            if 'SECTION 1:' in line.upper(): current_sec = 'SECTION 1'; continue
            if 'SECTION 2:' in line.upper(): current_sec = 'SECTION 2'; continue
            if 'SECTION 3:' in line.upper(): current_sec = 'SECTION 3'; continue
            if 'SECTION 4:' in line.upper(): current_sec = 'SECTION 4'; continue
            
            if current_sec:
                sections[current_sec] += line + "\n"
        
        # Fallback if parsing fails
        if not sections['SECTION 1']: sections['SECTION 1'] = generated_text

        # 6. Generate PDF
        print("Step 3: PDF Layout...", flush=True)
        pdf = ContentPDF()
        pdf.alias_nb_pages()
        
        # PAGE 1: Executive Summary
        pdf.add_page()
        pdf.chapter_title("The Snapshot")
        if audit['status'] != 'PASS':
            pdf.set_text_color(255, 0, 0)
            pdf.cell(0, 10, pdf.sanitize_text(f"NOTE: {audit['reason']}"), 0, 1)
        pdf.chapter_body(sections['SECTION 1'])
        
        # PAGE 2: Video Script
        pdf.add_page()
        pdf.chapter_title("The Core Content")
        # Note: Screenshots moved to dedicated Storyboard page
        pdf.chapter_body(sections['SECTION 2'])
        
        # PAGE 2b: Visual Storyboard
        if screenshots:
            pdf.add_page()
            pdf.chapter_title("Visual Storyboard")
            
            # Grid Layout (3 columns)
            x_start = 10
            y_start = 30
            img_w = 60 
            img_h = 33 # 16:9 aspect
            
            col = 0
            row = 0
            
            for shot in screenshots:
                if row > 4: # New page if too many rows
                    pdf.add_page()
                    pdf.chapter_title("Visual Storyboard (Cont.)")
                    row = 0
                    
                x = x_start + (col * (img_w + 5))
                y = y_start + (row * (img_h + 10))
                
                try:
                    pdf.image(shot, x=x, y=y, w=img_w, h=img_h)
                    # Add timestamp label?
                    # pdf.set_xy(x, y + img_h + 1)
                    # pdf.set_font('Arial', '', 8)
                    # pdf.cell(img_w, 5, f"Cue {row*3 + col + 1}", 0, 0, 'C')
                except Exception as e:
                    print(f"Error PDF image: {e}")
                    
                col += 1
                if col >= 3:
                    col = 0
                    row += 1

        
        # PAGE 3: Social Media
        pdf.add_page()
        pdf.chapter_title("Social Media Pack")
        pdf.chapter_body(sections['SECTION 3'])
        
        # PAGE 4: Strategic Intelligence
        if sections['SECTION 4'].strip():
            pdf.add_page()
            pdf.chapter_title("Strategic Intelligence")
            pdf.chapter_body(sections['SECTION 4'])
        
        output_filename = f"{job_id}.pdf"
        pdf.output(os.path.join(app.config['OUTPUT_FOLDER'], output_filename))

        # Cleanup
        for t in temp_files:
            if os.path.exists(t): os.remove(t)
        if os.path.exists(video_path): os.remove(video_path)

        return jsonify({
            'message': 'Success',
            'download_url': f'/download/{output_filename}',
            'download_transcript_url': f'/download/{transcript_filename}',
            'transcript_text': generated_text, # Sending FULL generated text for Chatbot context
            'audit_status': audit['status']
        })

    except Exception as e:
        print(f"Error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    question = data.get('question')
    context = data.get('context') # This is now the Generated Text
    
    if not question or not context:
        return jsonify({'error': 'Missing data'}), 400
        
    client = InferenceClient(model="Qwen/Qwen2.5-72B-Instruct")
    
    prompt = f"""You are a content assistant. The user has generated the following content:
{context}

User Question: {question}
Answer based on the content above. You can rewrite tweets, summarize script, etc."""

    msg = [{"role": "user", "content": prompt}]
    resp = client.chat_completion(messages=msg, max_tokens=800)
    return jsonify({'answer': resp.choices[0].message.content.strip()})

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860)
