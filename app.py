import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import os
import re
import sqlite3
import uuid
import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory, abort
from werkzeug.utils import secure_filename
from moviepy import VideoFileClip
import whisper
from fpdf import FPDF
from huggingface_hub import InferenceClient


# ============================================
# AUDITOR SKILL: Safety & Structure Validator
# ============================================
class AuditorSkill:
    """
    Enterprise-grade auditor that validates SOP documents for:
    1. Safety compliance - checks for dangerous/bypass language
    2. Structure compliance - ensures proper step formatting
    3. Quality standards - validates professional formatting
    """
    
    def __init__(self):
        self.dangerous_terms = [
            'ignore warning', 
            'bypass safety', 
            'force', 
            "don't worry",
            'skip verification',
            'override',
            'disable protection',
            'turn off safety',
            'ignore error'
        ]
        
        self.required_sections = [
            'step 1', '1.', 'step-1'
        ]
    
    def run_audit(self, text):
        """
        Run comprehensive audit on SOP document.
        Returns dict with status ('PASS' or 'FAIL') and reason.
        """
        text_lower = text.lower()
        
        # 1. Safety Check - Look for dangerous terms
        for term in self.dangerous_terms:
            if term in text_lower:
                return {
                    'status': 'FAIL', 
                    'reason': f'Safety violation detected: "{term}"',
                    'severity': 'HIGH'
                }
        
        # 2. Structure Check - Ensure numbered steps exist
        has_steps = any(marker in text_lower for marker in self.required_sections)
        if not has_steps:
            return {
                'status': 'FAIL', 
                'reason': 'Missing numbered steps (Step 1, 1., etc.)',
                'severity': 'MEDIUM'
            }
        
        # 3. Length Check - Ensure substantial content
        if len(text) < 100:
            return {
                'status': 'FAIL',
                'reason': 'Content too brief for professional SOP',
                'severity': 'LOW'
            }
        
        # 4. All checks passed
        return {
            'status': 'PASS', 
            'reason': 'All compliance checks passed',
            'severity': 'NONE'
        }


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
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
# Using 'tiny' model for faster CPU processing
try:
    model = whisper.load_model("tiny")
except Exception as e:
    print(f"Error loading Whisper model: {e}")
    model = None


# ============================================
# AI WRITER: One-Shot Learning SOP Generator
# ============================================
def humanize_transcript(raw_text, video_duration=0, target_language='English'):
    """
    Enterprise Writer Agent: Uses One-Shot Learning to generate professional SOPs.
    Supports multiple languages via target_language parameter.
    Falls back to raw_text if API fails.
    """
    try:
        print(f"Step 2b: Writer Agent generating SOP in {target_language}...", flush=True)
        
        # Initialize client (uses HF_TOKEN from environment)
        client = InferenceClient(model="mistralai/Mistral-7B-Instruct-v0.3")
        
        # Calculate approximate timestamps based on video duration
        duration_info = ""
        if video_duration > 0:
            t1 = int(video_duration * 0.10)
            t2 = int(video_duration * 0.50)
            t3 = int(video_duration * 0.90)
            duration_info = f"\n\nVideo Duration: {int(video_duration)} seconds. Reference timestamps: {t1}s, {t2}s, {t3}s."
        
        # Generate SOP ID based on current date
        sop_id = datetime.datetime.now().strftime("SOP-%Y-%m%d-V1")
        current_date = datetime.datetime.now().strftime("%B %d, %Y")
        
        # ONE-SHOT LEARNING PROMPT with language support
        prompt = f"""You are an expert Technical Writer specializing in Standard Operating Procedures (SOPs).

Act as a Technical Writer. Rewrite the transcript into a professional SOP in {target_language}.

Follow this EXACT format (but write the content in {target_language}):

### EXAMPLE OUTPUT:
---
**DOCUMENT METADATA**
- SOP-ID: SOP-2026-0101-V1
- Date: January 01, 2026
- Classification: Standard Operating Procedure

**TITLE:** How to Reset the Network Router

**OBJECTIVE:** Safely reset network equipment to restore connectivity.

**SCOPE:** This procedure applies to all IT support personnel handling network equipment maintenance.

**PROCEDURE:**

Step 1: Locate the small black reset button on the back panel of the router.

Step 2: Using a paperclip or pin, press and hold the button for 10 seconds.

Step 3: Wait until the LED indicator flashes amber, indicating reset initiation.

Step 4: Release the button and wait 60 seconds for the device to reboot.

Step 5: Verify connectivity by checking the status lights (green = operational).

**COMPLIANCE NOTES:**
- Always document the reset in the maintenance log.
- If issues persist after reset, escalate to Level 2 support.
---

### YOUR TASK:
Using the EXACT format above, rewrite this transcript into a professional SOP.
IMPORTANT: Write the entire SOP content in {target_language}.

SOP-ID to use: {sop_id}
Date: {current_date}
{duration_info}

TRANSCRIPT:
{raw_text}

PROFESSIONAL SOP (in {target_language}):"""

        # Call the model with increased tokens for detailed output
        response = client.text_generation(
            prompt,
            max_new_tokens=2048,
            temperature=0.5,
            do_sample=True,
        )
        
        polished_text = response.strip()
        
        # Validate we got a reasonable response
        if len(polished_text) > 100:
            print("✓ Writer Agent completed successfully!", flush=True)
            return polished_text
        else:
            print("⚠ AI response too short, using raw text", flush=True)
            return raw_text
            
    except Exception as e:
        print(f"⚠ Writer Agent failed: {e}", flush=True)
        print("→ Falling back to raw transcript", flush=True)
        return raw_text


# ============================================
# Q&A CHATBOT: Context-based answering
# ============================================
def answer_question(question, context):
    """
    Answer a question based only on the provided context.
    Uses Mistral-7B for accurate, context-grounded responses.
    """
    try:
        client = InferenceClient(model="mistralai/Mistral-7B-Instruct-v0.3")
        
        prompt = f"""You are a helpful assistant that answers questions about Standard Operating Procedures.
Answer the following question using ONLY the information provided in the context below.
If the answer is not in the context, say "I cannot find this information in the document."

Context:
{context}

Question: {question}

Answer:"""

        response = client.text_generation(
            prompt,
            max_new_tokens=512,
            temperature=0.3,
            do_sample=True,
        )
        
        return response.strip()
        
    except Exception as e:
        print(f"⚠ Chat error: {e}", flush=True)
        return f"Sorry, I encountered an error: {str(e)}"


# ============================================
# HELPER FUNCTION: Extract frame from video
# ============================================
def extract_frame(video_path, seconds, output_path):
    """
    Extract a single frame from video at specified timestamp.
    Returns the output path if successful, None otherwise.
    """
    try:
        clip = VideoFileClip(video_path)
        # Ensure we don't exceed video duration
        timestamp = min(seconds, clip.duration - 0.1)
        if timestamp < 0:
            timestamp = 0
        frame = clip.get_frame(timestamp)
        clip.close()
        
        # Save frame as image using PIL
        from PIL import Image
        import numpy as np
        img = Image.fromarray(frame.astype(np.uint8))
        img.save(output_path, 'JPEG', quality=85)
        return output_path
    except Exception as e:
        print(f"Error extracting frame at {seconds}s: {e}")
        return None


# ============================================
# CUSTOM PDF CLASS: Professional SOP Document
# ============================================
class PDF(FPDF):
    
    def __init__(self):
        super().__init__()
        self.audit_status = 'PASS'
        self.audit_reason = ''
    
    def header(self):
        """Add header to every page (except cover page)."""
        if self.page_no() > 1:  # Skip header on cover page
            self.set_font('Arial', 'B', 10)
            self.set_text_color(100, 100, 100)
            # Position at top right
            self.set_xy(-60, 10)
            self.cell(50, 10, 'Docu-Genie SOP', 0, 0, 'R')
            self.ln(15)
    
    def footer(self):
        """Add page numbers to every page."""
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')
    
    def create_cover_page(self, title, audit_status='PASS', audit_reason=''):
        """Create a professional cover page with audit status."""
        self.add_page()
        
        # Background accent line - color based on audit status
        if audit_status == 'PASS':
            self.set_fill_color(34, 197, 94)  # Green
        else:
            self.set_fill_color(239, 68, 68)  # Red
        self.rect(0, 100, 210, 5, 'F')
        
        # Title
        self.set_y(120)
        self.set_font('Arial', 'B', 28)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 15, title, 0, 'C')
        
        # Subtitle
        self.ln(10)
        self.set_font('Arial', '', 14)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, 'Standard Operating Procedure', 0, 1, 'C')
        
        # Audit Status Badge
        self.ln(15)
        if audit_status == 'PASS':
            self.set_fill_color(220, 252, 231)  # Light green bg
            self.set_text_color(22, 163, 74)  # Green text
            status_text = 'AUDIT STATUS: APPROVED'
        else:
            self.set_fill_color(254, 226, 226)  # Light red bg
            self.set_text_color(220, 38, 38)  # Red text
            status_text = 'AUDIT STATUS: DRAFT REJECTED'
        
        self.set_font('Arial', 'B', 12)
        # Center the badge
        badge_width = self.get_string_width(status_text) + 20
        x_pos = (210 - badge_width) / 2
        self.set_x(x_pos)
        self.cell(badge_width, 12, status_text, 0, 1, 'C', True)
        
        # Audit reason if failed
        if audit_status != 'PASS' and audit_reason:
            self.ln(5)
            self.set_font('Arial', 'I', 10)
            self.set_text_color(220, 38, 38)
            self.multi_cell(0, 6, f'Reason: {audit_reason}', 0, 'C')
        
        # Date
        self.ln(15)
        self.set_font('Arial', '', 12)
        self.set_text_color(80, 80, 80)
        today = datetime.datetime.now().strftime('%B %d, %Y')
        self.cell(0, 10, f'Generated on: {today}', 0, 1, 'C')
        
        # Branding
        self.set_y(-50)
        self.set_font('Arial', 'I', 10)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, 'Powered by Docu-Genie Enterprise AI', 0, 1, 'C')
    
    def add_section_header(self, title):
        """Add a styled section header."""
        self.ln(10)
        self.set_font('Arial', 'B', 16)
        self.set_text_color(79, 70, 229)  # Indigo color
        self.cell(0, 10, title, 0, 1, 'L')
        self.set_draw_color(79, 70, 229)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)
    
    def add_warning_banner(self, message):
        """Add a prominent warning banner."""
        self.ln(5)
        self.set_fill_color(254, 243, 199)  # Amber background
        self.set_text_color(180, 83, 9)  # Amber text
        self.set_font('Arial', 'B', 11)
        self.multi_cell(0, 8, f'WARNING: {message}', 0, 'L', True)
        self.set_text_color(50, 50, 50)
        self.ln(5)
    
    def add_transcript(self, text):
        """Add transcript text with proper formatting."""
        self.set_font('Arial', '', 11)
        self.set_text_color(50, 50, 50)
        # Handle unicode safely
        safe_text = text.encode('latin-1', 'replace').decode('latin-1')
        self.multi_cell(0, 7, safe_text)
    
    def add_screenshot(self, image_path, caption=""):
        """Add a screenshot with optional caption."""
        if os.path.exists(image_path):
            # Check if we need a new page (leave room for image)
            if self.get_y() > 200:
                self.add_page()
            
            # Add image centered, fitting page width
            page_width = 190  # A4 width minus margins
            self.image(image_path, x=10, w=page_width)
            
            # Add caption if provided
            if caption:
                self.ln(3)
                self.set_font('Arial', 'I', 9)
                self.set_text_color(100, 100, 100)
                self.cell(0, 5, caption, 0, 1, 'C')
            self.ln(5)


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
    
    # Get target language from form (default to English)
    target_language = request.form.get('language', 'English')
    
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
        
        # Track temporary files for cleanup
        temp_files = []
        
        # Initialize Auditor
        auditor = AuditorSkill()
        
        try:
            # =====================
            # STEP 1: Extract Audio
            # =====================
            print("Step 1: Extracting Audio...", flush=True)
            audio_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}.wav")
            temp_files.append(audio_path)
            
            clip = VideoFileClip(video_path)
            video_duration = clip.duration
            clip.audio.write_audiofile(audio_path, logger=None)
            clip.close()
            
            # =====================
            # STEP 2: Transcribe
            # =====================
            print("Step 2: Transcribing with Whisper...", flush=True)
            if model is None:
               raise Exception("Whisper model not loaded")
            
            result = model.transcribe(audio_path)
            raw_text = result['text']
            
            # =====================
            # STEP 2b: Writer Agent generates SOP (with language)
            # =====================
            draft_sop = humanize_transcript(raw_text, video_duration, target_language)
            
            # =====================
            # STEP 2c: Auditor validates SOP
            # =====================
            print("Step 2c: Auditor Agent validating SOP...", flush=True)
            audit_result = auditor.run_audit(draft_sop)
            print(f"→ Audit Result: {audit_result['status']} - {audit_result['reason']}", flush=True)
            
            # Prepare final content based on audit
            if audit_result['status'] == 'PASS':
                final_sop = draft_sop
                audit_status = 'PASS'
                audit_reason = audit_result['reason']
            else:
                # Add warning header to rejected draft
                final_sop = f"⚠️ DRAFT REJECTED: {audit_result['reason']}\n\n" + \
                           "=" * 50 + "\n" + \
                           "UNVALIDATED DRAFT (Review Required)\n" + \
                           "=" * 50 + "\n\n" + \
                           draft_sop
                audit_status = 'FAIL'
                audit_reason = audit_result['reason']
            
            # =====================
            # STEP 3: Extract Screenshots
            # =====================
            print("Step 3: Extracting Screenshots...", flush=True)
            screenshot_paths = []
            
            # Extract at 10%, 50%, 90% of video duration
            percentages = [0.10, 0.50, 0.90]
            for i, pct in enumerate(percentages):
                timestamp = video_duration * pct
                screenshot_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_frame_{i}.jpg")
                result_path = extract_frame(video_path, timestamp, screenshot_path)
                if result_path:
                    screenshot_paths.append((result_path, timestamp))
                    temp_files.append(result_path)
            
            # =====================
            # STEP 4: Generate PDF
            # =====================
            print("Step 4: Generating PDF...", flush=True)
            pdf_filename = f"{job_id}.pdf"
            pdf_path = os.path.join(app.config['OUTPUT_FOLDER'], pdf_filename)
            
            # Create professional PDF
            pdf = PDF()
            pdf.alias_nb_pages()  # Enable total page count
            
            # Title from filename (clean it up)
            doc_title = filename.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title()
            
            # Cover page with audit status
            pdf.create_cover_page(doc_title, audit_status, audit_reason)
            
            # Content page
            pdf.add_page()
            
            # Add warning banner if audit failed
            if audit_status != 'PASS':
                pdf.add_warning_banner(f"This document failed automated compliance checks: {audit_reason}")
            
            # Screenshots section
            if screenshot_paths:
                pdf.add_section_header('Video Screenshots')
                for img_path, timestamp in screenshot_paths:
                    minutes = int(timestamp // 60)
                    seconds = int(timestamp % 60)
                    caption = f"Screenshot at {minutes}:{seconds:02d}"
                    pdf.add_screenshot(img_path, caption)
            
            # Transcript section (using validated or warned content)
            pdf.add_section_header('Standard Operating Procedure')
            pdf.add_transcript(final_sop)
            
            # Save PDF
            pdf.output(pdf_path)
            
            # =====================
            # STEP 5: Cleanup
            # =====================
            print("Step 5: Cleaning up temporary files...", flush=True)
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except Exception as e:
                    print(f"Warning: Could not delete temp file {temp_file}: {e}")
            
            # Clean up video file too
            try:
                if os.path.exists(video_path):
                    os.remove(video_path)
            except Exception as e:
                print(f"Warning: Could not delete video file: {e}")
            
            # Update DB
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("UPDATE jobs SET status = ? WHERE id = ?", ('completed', job_id))
            conn.commit()
            conn.close()
            
            print(f"✓ PDF generation complete! Audit: {audit_status}", flush=True)
            
            # Return download URL AND transcript for chatbot
            return jsonify({
                'message': 'Processing complete',
                'download_url': f'/download/{pdf_filename}',
                'transcript_text': raw_text,
                'audit_status': audit_status,
                'audit_reason': audit_reason,
                'language': target_language
            })

        except Exception as e:
            print(f"Error processing job {job_id}: {e}", flush=True)
            
            # Cleanup on error
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except:
                    pass
            
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("UPDATE jobs SET status = ? WHERE id = ?", ('failed', job_id))
            conn.commit()
            conn.close()
            return jsonify({'error': str(e)}), 500


@app.route('/chat', methods=['POST'])
def chat():
    """
    Q&A Chatbot endpoint.
    Accepts: { "question": "...", "context": "..." }
    Returns: { "answer": "..." }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        question = data.get('question', '').strip()
        context = data.get('context', '').strip()
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        if not context:
            return jsonify({'error': 'Context is required'}), 400
        
        print(f"Chat Q: {question[:50]}...", flush=True)
        
        answer = answer_question(question, context)
        
        return jsonify({
            'answer': answer,
            'question': question
        })
        
    except Exception as e:
        print(f"Chat error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500


@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860)
