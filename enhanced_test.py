#!/usr/bin/env python3
"""
Enhanced test with better video content and detailed error analysis
"""

import requests
import json
import os
import subprocess
import tempfile
import time

BASE_URL = "https://syncvoice-1.preview.emergentagent.com/api"

def create_video_with_text_to_speech():
    """Create a video with actual speech using TTS"""
    try:
        test_dir = "/tmp/test_videos"
        os.makedirs(test_dir, exist_ok=True)
        
        # First create an audio file with speech
        speech_text = "Hello, this is a test video for the AI dubbing system. We are testing speech recognition."
        audio_path = os.path.join(test_dir, "speech.wav")
        
        # Use espeak to generate speech (if available)
        try:
            cmd = ['espeak', '-w', audio_path, speech_text]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                # Fallback: create a longer sine wave that might be recognized as speech
                cmd = [
                    'ffmpeg', '-f', 'lavfi', '-i', 
                    'sine=frequency=440:duration=3,sine=frequency=880:duration=2',
                    '-ar', '16000', '-ac', '1', audio_path, '-y'
                ]
                subprocess.run(cmd, capture_output=True, text=True)
                
        except FileNotFoundError:
            # espeak not available, use ffmpeg to create complex audio
            cmd = [
                'ffmpeg', '-f', 'lavfi', '-i', 
                'sine=frequency=440:duration=2,sine=frequency=660:duration=2,sine=frequency=880:duration=1',
                '-ar', '16000', '-ac', '1', audio_path, '-y'
            ]
            subprocess.run(cmd, capture_output=True, text=True)
        
        # Now create video with this audio
        video_path = os.path.join(test_dir, "speech_video.mp4")
        cmd = [
            'ffmpeg', '-f', 'lavfi', '-i', 'testsrc=duration=5:size=640x480:rate=30',
            '-i', audio_path,
            '-c:v', 'libx264', '-c:a', 'aac', '-shortest',
            video_path, '-y'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(video_path):
            print(f"✅ Created speech video: {video_path}")
            return video_path
        else:
            print(f"❌ Failed to create speech video: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating speech video: {str(e)}")
        return None

def test_complete_pipeline():
    """Test the complete pipeline with better video"""
    print("\n🚀 Testing complete dubbing pipeline...")
    
    video_path = create_video_with_text_to_speech()
    if not video_path:
        print("❌ Could not create test video")
        return
    
    try:
        # Step 1: Upload video
        print("📤 Uploading video...")
        with open(video_path, 'rb') as video_file:
            files = {'file': ('speech_video.mp4', video_file, 'video/mp4')}
            data = {
                'source_language': 'English',
                'target_language': 'Hindi'
            }
            
            response = requests.post(
                f"{BASE_URL}/upload-video",
                files=files,
                data=data,
                timeout=30
            )
        
        if response.status_code != 200:
            print(f"❌ Upload failed: {response.status_code} - {response.text}")
            return
        
        result = response.json()
        job_id = result.get('job_id')
        print(f"✅ Upload successful, job_id: {job_id}")
        
        # Step 2: Start processing
        print("⚙️ Starting dubbing process...")
        response = requests.post(f"{BASE_URL}/process-dubbing/{job_id}", timeout=120)
        
        if response.status_code == 200:
            print("✅ Dubbing process started successfully")
            
            # Monitor progress
            max_wait = 180  # 3 minutes
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                status_response = requests.get(f"{BASE_URL}/job-status/{job_id}", timeout=30)
                
                if status_response.status_code == 200:
                    job_status = status_response.json()
                    current_status = job_status.get('status')
                    progress = job_status.get('progress', 0)
                    
                    print(f"   📊 Progress: {progress}% - Status: {current_status}")
                    
                    if current_status == 'completed':
                        print("✅ Dubbing completed successfully!")
                        
                        # Test download
                        download_response = requests.get(f"{BASE_URL}/download/{job_id}", timeout=30)
                        if download_response.status_code == 200:
                            print("✅ Download endpoint working")
                        else:
                            print(f"❌ Download failed: {download_response.status_code}")
                        
                        return True
                        
                    elif current_status == 'error':
                        error_msg = job_status.get('error_message', 'Unknown error')
                        print(f"❌ Dubbing failed with error: {error_msg}")
                        return False
                
                time.sleep(10)  # Wait 10 seconds
            
            print("❌ Dubbing process timed out")
            return False
            
        else:
            print(f"❌ Failed to start dubbing: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Pipeline test error: {str(e)}")
        return False

def test_backend_dependencies():
    """Test if all backend dependencies are working"""
    print("\n🔍 Testing backend dependencies...")
    
    try:
        # Test ffmpeg
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ ffmpeg is available")
        else:
            print("❌ ffmpeg not available")
        
        # Test whisper
        try:
            import whisper
            print("✅ whisper module available")
        except ImportError:
            print("❌ whisper module not available")
        
        # Test emergentintegrations
        try:
            from emergentintegrations.llm.chat import LlmChat
            print("✅ emergentintegrations available")
        except ImportError:
            print("❌ emergentintegrations not available")
        
        # Test pyttsx3
        try:
            import pyttsx3
            print("✅ pyttsx3 available")
        except ImportError:
            print("❌ pyttsx3 not available")
            
    except Exception as e:
        print(f"❌ Dependency test error: {str(e)}")

def main():
    print("🔧 ENHANCED TESTING - AI Video Dubbing System")
    print("=" * 60)
    
    # Test dependencies first
    test_backend_dependencies()
    
    # Test complete pipeline
    test_complete_pipeline()

if __name__ == "__main__":
    main()