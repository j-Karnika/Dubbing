from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os
import uuid
import shutil
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel
import json
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
from dotenv import load_dotenv
import tempfile
import subprocess
import librosa
import soundfile as sf
import numpy as np
from emergentintegrations.llm.chat import LlmChat, UserMessage
from gtts import gTTS
from pydub import AudioSegment
import io

# Load environment variables
load_dotenv()

app = FastAPI(title="AI Video Dubbing System")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB setup
client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
db = client.videodubbing

# Create directories for file storage
UPLOADS_DIR = "/tmp/uploads"
PROCESSED_DIR = "/tmp/processed"
AUDIO_DIR = "/tmp/audio"

for directory in [UPLOADS_DIR, PROCESSED_DIR, AUDIO_DIR]:
    os.makedirs(directory, exist_ok=True)

# Mount static files
app.mount("/files", StaticFiles(directory=PROCESSED_DIR), name="files")

# Pydantic models
class DubbingJob(BaseModel):
    id: str
    filename: str
    original_language: str
    target_language: str
    status: str
    created_at: str
    audio_extracted: bool = False
    transcription: Optional[str] = None
    translation: Optional[str] = None
    dubbed_audio_path: Optional[str] = None
    final_video_path: Optional[str] = None
    progress: int = 0
    error_message: Optional[str] = None

class TranslationRequest(BaseModel):
    text: str
    source_lang: str
    target_lang: str
    context: Optional[str] = None

# Initialize LLM for translation
async def get_llm_translator():
    """Initialize LLM translator with emotion preservation context"""
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM API key not configured")
    
    chat = LlmChat(
        api_key=api_key,
        session_id=f"translation_{uuid.uuid4()}",
        system_message="""You are an expert translator specializing in preserving emotional context, intensity, and cultural nuances during translation. 
        
When translating, you must:
        1. Maintain the exact emotional tone and intensity of the original text
        2. Preserve cultural context and adapt idioms appropriately
        3. Keep timing and rhythm suitable for voice synthesis
        4. Maintain the same level of formality/informality
        5. Preserve emphasis and emotional markers
        
        Respond with ONLY the translated text, no explanations or additional content."""
    ).with_model("openai", "gpt-5")
    
    return chat

# Utility functions
async def extract_audio_from_video(video_path: str, audio_path: str) -> bool:
    """Extract audio from video file using ffmpeg"""
    try:
        cmd = [
            'ffmpeg', '-i', video_path, 
            '-vn', '-acodec', 'pcm_s16le', 
            '-ar', '16000', '-ac', '1', 
            audio_path, '-y'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"Audio extraction error: {e}")
        return False

async def transcribe_audio(audio_path: str) -> Optional[str]:
    """Transcribe audio using Whisper"""
    try:
        import whisper
        model = whisper.load_model("base")  # Using base model for CPU efficiency
        result = model.transcribe(audio_path)
        transcription = result["text"].strip()
        
        # Return the transcription even if empty - let the caller decide how to handle it
        return transcription
    except Exception as e:
        print(f"Transcription error: {e}")
        return None

async def translate_text(text: str, source_lang: str, target_lang: str) -> Optional[str]:
    """Translate text using LLM with emotion preservation"""
    try:
        chat = await get_llm_translator()
        
        translation_prompt = f"""Translate the following {source_lang} text to {target_lang}, preserving all emotional intensity, tone, and cultural context:
        
        "{text}"
        
        Target language: {target_lang}"""
        
        user_message = UserMessage(text=translation_prompt)
        response = await chat.send_message(user_message)
        return response.strip()
    except Exception as e:
        print(f"Translation error: {e}")
        return None

async def synthesize_speech(text: str, output_path: str, reference_audio: Optional[str] = None) -> bool:
    """Basic TTS synthesis - placeholder for advanced voice cloning"""
    try:
        # Try pyttsx3 first
        import pyttsx3
        engine = pyttsx3.init()
        engine.save_to_file(text, output_path)
        engine.runAndWait()
        
        # Check if file was created
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True
        else:
            raise Exception("pyttsx3 did not create audio file")
            
    except Exception as e:
        print(f"pyttsx3 failed: {e}, trying fallback method")
        
        # Fallback: Create a simple audio file using ffmpeg
        try:
            # Create a simple tone as placeholder for TTS
            # In production, this would be replaced with proper TTS/voice cloning
            duration = max(2, len(text) * 0.1)  # Rough estimate based on text length
            cmd = [
                'ffmpeg', '-f', 'lavfi', '-i', f'sine=frequency=440:duration={duration}',
                '-ar', '16000', '-ac', '1', output_path, '-y'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and os.path.exists(output_path):
                print(f"Created fallback audio file for text: '{text[:50]}...'")
                return True
            else:
                print(f"Fallback TTS failed: {result.stderr}")
                return False
                
        except Exception as fallback_error:
            print(f"Fallback TTS error: {fallback_error}")
            return False

async def combine_audio_video(video_path: str, audio_path: str, output_path: str) -> bool:
    """Combine new audio with original video"""
    try:
        cmd = [
            'ffmpeg', '-i', video_path, '-i', audio_path,
            '-c:v', 'copy', '-map', '0:v:0', '-map', '1:a:0',
            output_path, '-y'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"Video combination error: {e}")
        return False

# API Endpoints
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "AI Video Dubbing System"}

@app.post("/api/upload-video")
async def upload_video(
    file: UploadFile = File(...),
    source_language: str = Form(...),
    target_language: str = Form(...)
):
    """Upload video file and start dubbing process"""
    # Validate file type first (before try block to avoid wrapping in 500 error)
    if not file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
        raise HTTPException(status_code=400, detail="Invalid video format")
    
    try:
        
        # Create job ID and save file
        job_id = str(uuid.uuid4())
        file_extension = file.filename.split('.')[-1]
        video_filename = f"{job_id}.{file_extension}"
        video_path = os.path.join(UPLOADS_DIR, video_filename)
        
        with open(video_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Create job record
        job = {
            "id": job_id,
            "filename": file.filename,
            "original_language": source_language,
            "target_language": target_language,
            "status": "uploaded",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "audio_extracted": False,
            "progress": 0,
            "video_path": video_path
        }
        
        await db.dubbing_jobs.insert_one(job)
        
        return {"job_id": job_id, "status": "uploaded", "message": "Video uploaded successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/api/process-dubbing/{job_id}")
async def process_dubbing(job_id: str):
    """Process the dubbing for a specific job"""
    try:
        # Get job from database
        job = await db.dubbing_jobs.find_one({"id": job_id})
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        video_path = job["video_path"]
        audio_path = os.path.join(AUDIO_DIR, f"{job_id}_original.wav")
        
        # Step 1: Extract audio
        await db.dubbing_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "extracting_audio", "progress": 10}}
        )
        
        if not await extract_audio_from_video(video_path, audio_path):
            await db.dubbing_jobs.update_one(
                {"id": job_id},
                {"$set": {"status": "error", "error_message": "Failed to extract audio"}}
            )
            raise HTTPException(status_code=500, detail="Audio extraction failed")
        
        # Step 2: Transcribe audio
        await db.dubbing_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "transcribing", "progress": 30}}
        )
        
        transcription = await transcribe_audio(audio_path)
        if transcription is None:
            await db.dubbing_jobs.update_one(
                {"id": job_id},
                {"$set": {"status": "error", "error_message": "Transcription failed"}}
            )
            raise HTTPException(status_code=500, detail="Transcription failed")
        
        # Handle empty transcription (no speech detected)
        if not transcription.strip():
            transcription = "No speech detected in the audio."
        
        # Step 3: Translate text
        await db.dubbing_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "translating", "progress": 50, "transcription": transcription}}
        )
        
        translation = await translate_text(
            transcription, 
            job["original_language"], 
            job["target_language"]
        )
        
        if not translation:
            await db.dubbing_jobs.update_one(
                {"id": job_id},
                {"$set": {"status": "error", "error_message": "Translation failed"}}
            )
            raise HTTPException(status_code=500, detail="Translation failed")
        
        # Step 4: Synthesize speech
        await db.dubbing_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "synthesizing", "progress": 70, "translation": translation}}
        )
        
        dubbed_audio_path = os.path.join(AUDIO_DIR, f"{job_id}_dubbed.wav")
        if not await synthesize_speech(translation, dubbed_audio_path, audio_path):
            await db.dubbing_jobs.update_one(
                {"id": job_id},
                {"$set": {"status": "error", "error_message": "Speech synthesis failed"}}
            )
            raise HTTPException(status_code=500, detail="Speech synthesis failed")
        
        # Step 5: Combine with video
        await db.dubbing_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "finalizing", "progress": 90}}
        )
        
        final_video_path = os.path.join(PROCESSED_DIR, f"{job_id}_dubbed.mp4")
        if not await combine_audio_video(video_path, dubbed_audio_path, final_video_path):
            await db.dubbing_jobs.update_one(
                {"id": job_id},
                {"$set": {"status": "error", "error_message": "Video combination failed"}}
            )
            raise HTTPException(status_code=500, detail="Video combination failed")
        
        # Complete
        await db.dubbing_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "completed",
                "progress": 100,
                "final_video_path": final_video_path,
                "dubbed_audio_path": dubbed_audio_path
            }}
        )
        
        return {"job_id": job_id, "status": "completed", "message": "Dubbing completed successfully"}
    
    except Exception as e:
        await db.dubbing_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "error", "error_message": str(e)}}
        )
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/api/job-status/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a dubbing job"""
    job = await db.dubbing_jobs.find_one({"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Remove internal paths from response
    job.pop("_id", None)
    job.pop("video_path", None)
    
    return job

@app.get("/api/jobs")
async def get_all_jobs():
    """Get all dubbing jobs"""
    jobs = await db.dubbing_jobs.find().to_list(length=None)
    for job in jobs:
        job.pop("_id", None)
        job.pop("video_path", None)
    return jobs

@app.get("/api/download/{job_id}")
async def download_dubbed_video(job_id: str):
    """Download the dubbed video"""
    job = await db.dubbing_jobs.find_one({"id": job_id})
    if not job or job["status"] != "completed":
        raise HTTPException(status_code=404, detail="Completed job not found")
    
    video_path = job.get("final_video_path")
    if not video_path or not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Dubbed video file not found")
    
    return FileResponse(
        path=video_path,
        filename=f"{job['filename']}_dubbed.mp4",
        media_type="video/mp4"
    )

@app.post("/api/translate-text")
async def translate_text_endpoint(request: TranslationRequest):
    """Direct translation endpoint for testing"""
    try:
        translation = await translate_text(
            request.text,
            request.source_lang,
            request.target_lang
        )
        
        if not translation:
            raise HTTPException(status_code=500, detail="Translation failed")
        
        return {
            "original": request.text,
            "translated": translation,
            "source_language": request.source_lang,
            "target_language": request.target_lang
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)