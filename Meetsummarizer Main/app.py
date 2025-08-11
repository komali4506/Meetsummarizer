from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
import whisper
import os
import tempfile
import uuid
from datetime import datetime, timedelta
from transformers import pipeline
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
import logging
import re

# Google Calendar imports
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Global variables for models
whisper_model = None
summarizer = None

# Google Calendar configuration
SCOPES = ['https://www.googleapis.com/auth/calendar.events']
CALENDAR_CREDS_FILE = 'client_secret.json'
CALENDAR_TOKEN_FILE = 'token.json'

# Directories
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"

# Create directories if they don't exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


@app.route('/')
def index():
    """Serve the main HTML page"""
    return render_template('index.html')

def create_google_meet():
    """Create a Google Meet link using your existing OAuth setup"""
    try:
        creds = None
        if os.path.exists(CALENDAR_TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(CALENDAR_TOKEN_FILE, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(CALENDAR_CREDS_FILE):
                    raise Exception("client_secret.json file not found. Please add your Google OAuth credentials.")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    CALENDAR_CREDS_FILE, SCOPES)
                creds = flow.run_local_server(port=8081)
            
            with open(CALENDAR_TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())

        service = build('calendar', 'v3', credentials=creds)

        # Create meeting for current time + 5 minutes, duration 1 hour
        start_time = (datetime.now() + timedelta(minutes=5)).isoformat()
        end_time = (datetime.now() + timedelta(hours=1, minutes=5)).isoformat()

        event = {
            'summary': 'Meeting Recording Session',
            'description': 'Auto-generated meeting for recording and transcription',
            'start': {
                'dateTime': start_time,
                'timeZone': 'Asia/Kolkata',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'Asia/Kolkata',
            },
            'conferenceData': {
                'createRequest': {
                    'conferenceSolutionKey': {
                        'type': 'hangoutsMeet'
                    },
                    'requestId': f'meet-recorder-{uuid.uuid4().hex[:8]}'
                }
            }
        }

        event_result = service.events().insert(
            calendarId='primary',
            body=event,
            conferenceDataVersion=1
        ).execute()

        meet_link = event_result.get('hangoutLink')
        if not meet_link:
            # Fallback: try to get from conferenceData
            conference_data = event_result.get('conferenceData', {})
            entry_points = conference_data.get('entryPoints', [])
            for entry in entry_points:
                if entry.get('entryPointType') == 'video':
                    meet_link = entry.get('uri')
                    break

        return meet_link

    except Exception as e:
        logger.error(f"Error creating Google Meet: {e}")
        raise e

def load_models():
    """Load Whisper and summarization models"""
    global whisper_model, summarizer
    
    try:
        logger.info("Loading Whisper model...")
        whisper_model = whisper.load_model("base")  # You can use "small", "medium", "large" for better quality
        logger.info("Whisper model loaded successfully")
        
        logger.info("Loading summarization model...")
        summarizer = pipeline(
            "summarization", 
            model="facebook/bart-large-cnn",
            device=0 if os.system("nvidia-smi") == 0 else -1  # Use GPU if available
        )
        logger.info("Summarization model loaded successfully")
        
    except Exception as e:
        logger.error(f"Error loading models: {e}")
        # Fallback to smaller models if there are issues
        try:
            whisper_model = whisper.load_model("tiny")
            summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
            logger.info("Fallback models loaded successfully")
        except Exception as fallback_error:
            logger.error(f"Failed to load fallback models: {fallback_error}")

def transcribe_audio(audio_path):
    """Transcribe audio using Whisper"""
    try:
        logger.info(f"Transcribing audio: {audio_path}")
        result = whisper_model.transcribe(audio_path)
        return result["text"]
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        return None

def summarize_transcript(transcript):
    """Summarize the transcript using the loaded summarization model"""
    try:
        logger.info("Summarizing transcript...")
        
        # Check if summarizer is loaded
        if summarizer is None:
            logger.error("Summarizer model not loaded")
            return None
        
        # Split long transcripts into chunks if needed (BART has token limits)
        max_chunk_length = 1000  # Approximate token limit
        words = transcript.split()
        
        if len(words) <= max_chunk_length:
            # Short enough to summarize directly
            summary = summarizer(transcript, max_length=200, min_length=50, do_sample=False)
            return summary[0]['summary_text']
        else:
            # Split into chunks and summarize each chunk
            chunks = []
            chunk_summaries = []
            
            for i in range(0, len(words), max_chunk_length):
                chunk = ' '.join(words[i:i + max_chunk_length])
                chunks.append(chunk)
            
            logger.info(f"Splitting transcript into {len(chunks)} chunks for summarization")
            
            # Summarize each chunk
            for i, chunk in enumerate(chunks):
                try:
                    chunk_summary = summarizer(chunk, max_length=150, min_length=30, do_sample=False)
                    chunk_summaries.append(chunk_summary[0]['summary_text'])
                    logger.info(f"Summarized chunk {i+1}/{len(chunks)}")
                except Exception as chunk_error:
                    logger.error(f"Error summarizing chunk {i+1}: {chunk_error}")
                    # If chunk fails, use first few sentences as fallback
                    sentences = chunk.split('.')[:3]
                    fallback_summary = '. '.join(sentences).strip()
                    if fallback_summary:
                        chunk_summaries.append(fallback_summary + '.')
            
            # Combine chunk summaries
            combined_summary = ' '.join(chunk_summaries)
            
            # If combined summary is still too long, summarize it again
            if len(combined_summary.split()) > 300:
                final_summary = summarizer(combined_summary, max_length=200, min_length=50, do_sample=False)
                return final_summary[0]['summary_text']
            else:
                return combined_summary
            
    except Exception as e:
        logger.error(f"Error summarizing transcript: {e}")
        # Fallback: return first few sentences of transcript
        sentences = transcript.split('.')[:5]
        fallback = '. '.join(sentences).strip()
        return fallback + '.' if fallback else transcript[:500] + "..."

def extract_bullet_points(summary):
    """Extract bullet points from the summary"""
    try:
        logger.info("Extracting bullet points from summary...")
        
        # Split summary into sentences
        sentences = re.split(r'[.!?]+', summary)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Filter and process sentences into bullet points
        bullet_points = []
        
        for sentence in sentences:
            # Skip very short sentences
            if len(sentence.split()) < 3:
                continue
            
            # Clean up the sentence
            sentence = sentence.strip()
            
            # Ensure proper capitalization
            if len(sentence) > 1:
                sentence = sentence[0].upper() + sentence[1:]
            
            # Ensure proper punctuation
            if not sentence.endswith(('.', '!', '?')):
                sentence += '.'
            
            bullet_points.append(sentence)
        
        # Limit to maximum 10 bullet points for readability
        bullet_points = bullet_points[:10]
        
        # If no bullet points extracted, create some from the summary
        if not bullet_points and summary:
            # Split by common connectors and create bullet points
            parts = re.split(r'\b(and|also|furthermore|additionally|moreover|however|but|while)\b', summary)
            for part in parts:
                part = part.strip()
                if len(part.split()) >= 5 and part not in ['and', 'also', 'furthermore', 'additionally', 'moreover', 'however', 'but', 'while']:
                    if len(part) > 1:
                        part = part[0].upper() + part[1:]
                    if not part.endswith(('.', '!', '?')):
                        part += '.'
                    bullet_points.append(part)
                    if len(bullet_points) >= 8:
                        break
        
        logger.info(f"Extracted {len(bullet_points)} bullet points")
        return bullet_points
        
    except Exception as e:
        logger.error(f"Error extracting bullet points: {e}")
        # Fallback: return first few sentences
        sentences = summary.split('.')[:5] if summary else ["No bullet points could be extracted."]
        return [s.strip() + '.' for s in sentences if s.strip()]

def create_bullet_points_pdf(bullet_points, filename):
    """Create PDF with bullet points"""
    try:
        logger.info(f"Creating bullet points PDF: {filename}")
        
        # Create PDF document
        doc = SimpleDocTemplate(filename, pagesize=letter, 
                              leftMargin=0.75*inch, rightMargin=0.75*inch,
                              topMargin=1*inch, bottomMargin=1*inch)
        styles = getSampleStyleSheet()
        story = []
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=28,
            textColor=HexColor('#1a365d'),
            alignment=TA_CENTER,
            spaceAfter=40,
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=HexColor('#4a5568'),
            alignment=TA_CENTER,
            spaceAfter=30,
            fontName='Helvetica'
        )
        
        bullet_style = ParagraphStyle(
            'BulletStyle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=HexColor('#2d3748'),
            leftIndent=0,
            spaceBefore=8,
            spaceAfter=8,
            fontName='Helvetica',
            leading=18
        )
        
        # Title
        story.append(Paragraph("📋 Meeting Summary - Key Points", title_style))
        
        # Subtitle with date and time
        story.append(Paragraph(
            f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", 
            subtitle_style
        ))
        
        story.append(Spacer(1, 0.3*inch))
        
        # Bullet points section
        if bullet_points:
            for i, point in enumerate(bullet_points, 1):
                # Format each point with a bullet
                formatted_point = f"• {point}"
                story.append(Paragraph(formatted_point, bullet_style))
        else:
            story.append(Paragraph("• No key points could be extracted from the recording.", bullet_style))
        
        # Add some spacing at the bottom
        story.append(Spacer(1, 0.5*inch))
        
        # Footer
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=10,
            textColor=HexColor('#718096'),
            alignment=TA_CENTER,
            fontName='Helvetica-Oblique'
        )
        
        story.append(Paragraph(
            "Generated by Google Meet Recorder", 
            footer_style
        ))
        
        # Build PDF
        doc.build(story)
        logger.info(f"Bullet points PDF created successfully: {filename}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating bullet points PDF: {e}")
        return False

@app.route('/create-meet', methods=['POST'])
def create_meet_endpoint():
    """Create a Google Meet link"""
    try:
        meet_link = create_google_meet()
        if meet_link:
            return jsonify({
                "success": True,
                "meet_link": meet_link,
                "message": "Google Meet created successfully!"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to create Google Meet link"
            }), 500
    except Exception as e:
        logger.error(f"Error in create_meet_endpoint: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "whisper_loaded": whisper_model is not None,
        "summarizer_loaded": summarizer is not None
    })

@app.route('/process-audio', methods=['POST'])
def process_audio():
    """Process uploaded audio file and generate bullet points PDF"""
    try:
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({"error": "No audio file selected"}), 400
        
        # Generate unique filename
        unique_id = str(uuid.uuid4())
        audio_filename = f"{unique_id}.webm"
        audio_path = os.path.join(UPLOAD_DIR, audio_filename)
        
        # Save uploaded file
        audio_file.save(audio_path)
        logger.info(f"Audio file saved: {audio_path}")
        
        # Check if models are loaded
        if whisper_model is None:
            return jsonify({"error": "Whisper model not loaded. Please check server logs."}), 500
        
        if summarizer is None:
            return jsonify({"error": "Summarization model not loaded. Please check server logs."}), 500
        
        # Step 1: Transcribe audio
        transcription = transcribe_audio(audio_path)
        if transcription is None:
            return jsonify({"error": "Failed to transcribe audio"}), 500
        
        logger.info("Transcription completed")
        
        # Step 2: Summarize the transcript
        summary = summarize_transcript(transcription)
        if summary is None:
            return jsonify({"error": "Failed to summarize transcript"}), 500
        
        logger.info("Summarization completed")
        
        # Step 3: Extract bullet points from summary
        bullet_points = extract_bullet_points(summary)
        logger.info(f"Extracted {len(bullet_points)} bullet points")
        
        # Step 4: Create PDF with bullet points
        pdf_filename = f"meeting_summary_{unique_id}.pdf"
        pdf_path = os.path.join(OUTPUT_DIR, pdf_filename)
        
        if create_bullet_points_pdf(bullet_points, pdf_path):
            # Clean up audio file
            try:
                os.remove(audio_path)
            except:
                pass
            
            return jsonify({
                "success": True,
                "transcription": transcription,  # For debugging if needed
                "summary": summary,             # The generated summary
                "bullet_points": bullet_points, # The extracted bullet points
                "pdf_path": pdf_filename
            })
        else:
            return jsonify({"error": "Failed to create bullet points PDF"}), 500
            
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    """Download generated PDF file"""
    try:
        file_path = os.path.join(OUTPUT_DIR, filename)
        if os.path.exists(file_path):
            return send_file(
                file_path,
                as_attachment=True,
                download_name=f"meeting-summary-{datetime.now().strftime('%Y%m%d-%H%M%S')}.pdf"
            )
        else:
            return jsonify({"error": "File not found"}), 404
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    logger.info("Starting Google Meet Recorder Backend...")
    
    # Load models on startup
    load_models()
    
    # Start Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)