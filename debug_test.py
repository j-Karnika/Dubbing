#!/usr/bin/env python3
"""
Debug test to identify specific issues with the dubbing pipeline
"""

import requests
import json
import os
import subprocess
import tempfile

BASE_URL = "https://syncvoice-1.preview.emergentagent.com/api"

def create_test_video_with_speech():
    """Create a test video with actual speech for better transcription"""
    try:
        test_dir = "/tmp/test_videos"
        os.makedirs(test_dir, exist_ok=True)
        
        # Create a test video with synthesized speech
        test_video_path = os.path.join(test_dir, "speech_test_video.mp4")
        
        # Generate a 5-second test video with a sine wave audio (simulating speech)
        cmd = [
            'ffmpeg', '-f', 'lavfi', '-i', 'testsrc=duration=5:size=320x240:rate=1',
            '-f', 'lavfi', '-i', 'sine=frequency=440:duration=5',
            '-c:v', 'libx264', '-c:a', 'aac', '-shortest',
            test_video_path, '-y'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(test_video_path):
            print(f"✅ Created test video: {test_video_path}")
            return test_video_path
        else:
            print(f"❌ Failed to create test video: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating test video: {str(e)}")
        return None

def test_file_validation():
    """Test the file validation issue"""
    print("\n🔍 Testing file validation...")
    
    # Test with invalid file
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
        temp_file.write(b"This is not a video file")
        temp_file_path = temp_file.name
    
    try:
        with open(temp_file_path, 'rb') as invalid_file:
            files = {'file': ('test.txt', invalid_file, 'text/plain')}
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
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        # Clean up
        os.unlink(temp_file_path)
        
    except Exception as e:
        print(f"❌ File validation test error: {str(e)}")

def test_audio_extraction_locally():
    """Test audio extraction locally to debug the issue"""
    print("\n🔍 Testing audio extraction locally...")
    
    video_path = create_test_video_with_speech()
    if not video_path:
        return
    
    audio_path = "/tmp/test_audio.wav"
    
    try:
        cmd = [
            'ffmpeg', '-i', video_path, 
            '-vn', '-acodec', 'pcm_s16le', 
            '-ar', '16000', '-ac', '1', 
            audio_path, '-y'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Audio extraction successful: {audio_path}")
            print(f"Audio file size: {os.path.getsize(audio_path)} bytes")
            
            # Test Whisper transcription locally
            try:
                import whisper
                print("🔍 Testing Whisper transcription...")
                model = whisper.load_model("base")
                result = model.transcribe(audio_path)
                print(f"Transcription result: {result['text']}")
                
            except Exception as e:
                print(f"❌ Whisper transcription failed: {str(e)}")
                
        else:
            print(f"❌ Audio extraction failed: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Audio extraction test error: {str(e)}")

def test_translation_with_simple_text():
    """Test translation with very simple text"""
    print("\n🔍 Testing translation with simple text...")
    
    try:
        translation_data = {
            "text": "Hello world",
            "source_lang": "English",
            "target_lang": "Hindi"
        }
        
        response = requests.post(
            f"{BASE_URL}/translate-text",
            json=translation_data,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Translation successful:")
            print(f"   Original: {result['original']}")
            print(f"   Translated: {result['translated']}")
        else:
            print(f"❌ Translation failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Translation test error: {str(e)}")

def main():
    print("🔍 DEBUG TESTING - AI Video Dubbing System")
    print("=" * 50)
    
    # Test 1: File validation issue
    test_file_validation()
    
    # Test 2: Audio extraction and transcription
    test_audio_extraction_locally()
    
    # Test 3: Translation
    test_translation_with_simple_text()

if __name__ == "__main__":
    main()