#!/usr/bin/env python3
"""
Simple test focusing on the core issues
"""

import requests
import json
import os
import subprocess
import time

BASE_URL = "https://syncvoice-1.preview.emergentagent.com/api"

def create_simple_test_video():
    """Create a simple test video with audio"""
    try:
        test_dir = "/tmp/test_videos"
        os.makedirs(test_dir, exist_ok=True)
        
        video_path = os.path.join(test_dir, "simple_test.mp4")
        
        # Create a simple 3-second video with audio
        cmd = [
            'ffmpeg', '-f', 'lavfi', '-i', 'testsrc=duration=3:size=320x240:rate=1',
            '-f', 'lavfi', '-i', 'sine=frequency=440:duration=3',
            '-c:v', 'libx264', '-c:a', 'aac', '-shortest',
            video_path, '-y'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(video_path):
            print(f"✅ Created test video: {video_path}")
            return video_path
        else:
            print(f"❌ Failed to create test video: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating test video: {str(e)}")
        return None

def test_step_by_step():
    """Test each step of the pipeline individually"""
    print("🔍 Step-by-step pipeline testing...")
    
    # Step 1: Create and upload video
    video_path = create_simple_test_video()
    if not video_path:
        return
    
    print("\n📤 Step 1: Upload video")
    try:
        with open(video_path, 'rb') as video_file:
            files = {'file': ('simple_test.mp4', video_file, 'video/mp4')}
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
        
        if response.status_code == 200:
            result = response.json()
            job_id = result.get('job_id')
            print(f"✅ Upload successful, job_id: {job_id}")
        else:
            print(f"❌ Upload failed: {response.status_code} - {response.text}")
            return
            
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        return
    
    # Step 2: Check job status
    print("\n📊 Step 2: Check job status")
    try:
        response = requests.get(f"{BASE_URL}/job-status/{job_id}", timeout=30)
        if response.status_code == 200:
            job_data = response.json()
            print(f"✅ Job status: {job_data}")
        else:
            print(f"❌ Job status failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Job status error: {str(e)}")
    
    # Step 3: Test translation separately
    print("\n🔤 Step 3: Test translation")
    try:
        translation_data = {
            "text": "This is a simple test",
            "source_lang": "English",
            "target_lang": "Hindi"
        }
        
        response = requests.post(
            f"{BASE_URL}/translate-text",
            json=translation_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Translation: '{result['original']}' -> '{result['translated']}'")
        else:
            print(f"❌ Translation failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Translation error: {str(e)}")
    
    # Step 4: Try processing (this is where it fails)
    print("\n⚙️ Step 4: Start processing")
    try:
        response = requests.post(f"{BASE_URL}/process-dubbing/{job_id}", timeout=60)
        
        if response.status_code == 200:
            print("✅ Processing started successfully")
            
            # Monitor for a short time
            for i in range(6):  # Check 6 times (1 minute)
                time.sleep(10)
                status_response = requests.get(f"{BASE_URL}/job-status/{job_id}", timeout=30)
                
                if status_response.status_code == 200:
                    job_status = status_response.json()
                    current_status = job_status.get('status')
                    progress = job_status.get('progress', 0)
                    
                    print(f"   📊 Progress: {progress}% - Status: {current_status}")
                    
                    if current_status == 'completed':
                        print("✅ Processing completed!")
                        return
                    elif current_status == 'error':
                        error_msg = job_status.get('error_message', 'Unknown error')
                        print(f"❌ Processing failed: {error_msg}")
                        return
            
            print("⏰ Processing still in progress after 1 minute")
            
        else:
            print(f"❌ Processing failed to start: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Processing error: {str(e)}")

def main():
    print("🧪 SIMPLE STEP-BY-STEP TESTING")
    print("=" * 40)
    
    test_step_by_step()

if __name__ == "__main__":
    main()