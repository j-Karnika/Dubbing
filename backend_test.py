#!/usr/bin/env python3
"""
Comprehensive Backend Testing for AI Video Dubbing System
Tests all backend endpoints and the complete dubbing pipeline
"""

import requests
import json
import time
import os
import tempfile
from pathlib import Path

# Configuration
BASE_URL = "https://syncvoice-1.preview.emergentagent.com/api"
TEST_TIMEOUT = 30

class VideodubbingTester:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = {}
        self.job_ids = []
        
    def log_test(self, test_name, success, message, details=None):
        """Log test results"""
        self.test_results[test_name] = {
            "success": success,
            "message": message,
            "details": details or {}
        }
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
        if details:
            print(f"   Details: {details}")
    
    def test_health_endpoint(self):
        """Test the health check endpoint"""
        try:
            response = self.session.get(f"{BASE_URL}/health", timeout=TEST_TIMEOUT)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.log_test("Health Check", True, "Health endpoint working correctly", data)
                else:
                    self.log_test("Health Check", False, "Health endpoint returned unexpected status", data)
            else:
                self.log_test("Health Check", False, f"Health endpoint returned status {response.status_code}", 
                            {"status_code": response.status_code, "response": response.text})
        except Exception as e:
            self.log_test("Health Check", False, f"Health endpoint failed with exception: {str(e)}")
    
    def create_test_video_file(self):
        """Create a small test video file for testing"""
        try:
            # Create a temporary directory for test files
            test_dir = "/tmp/test_videos"
            os.makedirs(test_dir, exist_ok=True)
            
            # Create a simple test video using ffmpeg (1 second black video with audio tone)
            test_video_path = os.path.join(test_dir, "test_video.mp4")
            
            # Generate a 3-second test video with audio
            cmd = [
                'ffmpeg', '-f', 'lavfi', '-i', 'testsrc=duration=3:size=320x240:rate=1',
                '-f', 'lavfi', '-i', 'sine=frequency=1000:duration=3',
                '-c:v', 'libx264', '-c:a', 'aac', '-shortest',
                test_video_path, '-y'
            ]
            
            import subprocess
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and os.path.exists(test_video_path):
                return test_video_path
            else:
                print(f"Failed to create test video: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"Error creating test video: {str(e)}")
            return None
    
    def test_video_upload(self):
        """Test video upload endpoint with different formats"""
        test_video_path = self.create_test_video_file()
        
        if not test_video_path:
            self.log_test("Video Upload", False, "Could not create test video file")
            return None
        
        try:
            # Test MP4 upload
            with open(test_video_path, 'rb') as video_file:
                files = {'file': ('test_video.mp4', video_file, 'video/mp4')}
                data = {
                    'source_language': 'English',
                    'target_language': 'Hindi'
                }
                
                response = self.session.post(
                    f"{BASE_URL}/upload-video",
                    files=files,
                    data=data,
                    timeout=TEST_TIMEOUT
                )
            
            if response.status_code == 200:
                result = response.json()
                job_id = result.get('job_id')
                if job_id:
                    self.job_ids.append(job_id)
                    self.log_test("Video Upload", True, "Video uploaded successfully", result)
                    return job_id
                else:
                    self.log_test("Video Upload", False, "No job_id returned in response", result)
            else:
                self.log_test("Video Upload", False, f"Upload failed with status {response.status_code}", 
                            {"status_code": response.status_code, "response": response.text})
                
        except Exception as e:
            self.log_test("Video Upload", False, f"Upload failed with exception: {str(e)}")
        
        return None
    
    def test_invalid_file_upload(self):
        """Test upload with invalid file format"""
        try:
            # Create a text file to test invalid format
            with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
                temp_file.write(b"This is not a video file")
                temp_file_path = temp_file.name
            
            with open(temp_file_path, 'rb') as invalid_file:
                files = {'file': ('test.txt', invalid_file, 'text/plain')}
                data = {
                    'source_language': 'English',
                    'target_language': 'Hindi'
                }
                
                response = self.session.post(
                    f"{BASE_URL}/upload-video",
                    files=files,
                    data=data,
                    timeout=TEST_TIMEOUT
                )
            
            # Clean up temp file
            os.unlink(temp_file_path)
            
            if response.status_code == 400:
                self.log_test("Invalid File Upload", True, "Correctly rejected invalid file format")
            else:
                self.log_test("Invalid File Upload", False, f"Should have rejected invalid file, got status {response.status_code}")
                
        except Exception as e:
            self.log_test("Invalid File Upload", False, f"Invalid file test failed: {str(e)}")
    
    def test_job_status(self, job_id):
        """Test job status endpoint"""
        if not job_id:
            self.log_test("Job Status", False, "No job_id provided for testing")
            return
        
        try:
            response = self.session.get(f"{BASE_URL}/job-status/{job_id}", timeout=TEST_TIMEOUT)
            
            if response.status_code == 200:
                job_data = response.json()
                required_fields = ['id', 'filename', 'status', 'progress']
                
                if all(field in job_data for field in required_fields):
                    self.log_test("Job Status", True, "Job status retrieved successfully", job_data)
                else:
                    missing_fields = [field for field in required_fields if field not in job_data]
                    self.log_test("Job Status", False, f"Missing required fields: {missing_fields}", job_data)
            else:
                self.log_test("Job Status", False, f"Job status request failed with status {response.status_code}")
                
        except Exception as e:
            self.log_test("Job Status", False, f"Job status test failed: {str(e)}")
    
    def test_nonexistent_job_status(self):
        """Test job status with non-existent job ID"""
        try:
            fake_job_id = "non-existent-job-id"
            response = self.session.get(f"{BASE_URL}/job-status/{fake_job_id}", timeout=TEST_TIMEOUT)
            
            if response.status_code == 404:
                self.log_test("Non-existent Job Status", True, "Correctly returned 404 for non-existent job")
            else:
                self.log_test("Non-existent Job Status", False, f"Should return 404, got {response.status_code}")
                
        except Exception as e:
            self.log_test("Non-existent Job Status", False, f"Non-existent job test failed: {str(e)}")
    
    def test_all_jobs(self):
        """Test getting all jobs"""
        try:
            response = self.session.get(f"{BASE_URL}/jobs", timeout=TEST_TIMEOUT)
            
            if response.status_code == 200:
                jobs = response.json()
                if isinstance(jobs, list):
                    self.log_test("All Jobs", True, f"Retrieved {len(jobs)} jobs successfully")
                else:
                    self.log_test("All Jobs", False, "Jobs endpoint should return a list")
            else:
                self.log_test("All Jobs", False, f"Jobs request failed with status {response.status_code}")
                
        except Exception as e:
            self.log_test("All Jobs", False, f"All jobs test failed: {str(e)}")
    
    def test_translation_endpoint(self):
        """Test direct translation endpoint"""
        try:
            translation_data = {
                "text": "Hello, how are you feeling today? I'm excited to see you!",
                "source_lang": "English",
                "target_lang": "Hindi",
                "context": "Casual conversation with emotional tone"
            }
            
            response = self.session.post(
                f"{BASE_URL}/translate-text",
                json=translation_data,
                timeout=TEST_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                required_fields = ['original', 'translated', 'source_language', 'target_language']
                
                if all(field in result for field in required_fields):
                    if result['translated'] and result['translated'] != result['original']:
                        self.log_test("Text Translation", True, "Translation completed successfully", result)
                    else:
                        self.log_test("Text Translation", False, "Translation appears to be empty or same as original", result)
                else:
                    missing_fields = [field for field in required_fields if field not in result]
                    self.log_test("Text Translation", False, f"Missing required fields: {missing_fields}", result)
            else:
                self.log_test("Text Translation", False, f"Translation failed with status {response.status_code}", 
                            {"status_code": response.status_code, "response": response.text})
                
        except Exception as e:
            self.log_test("Text Translation", False, f"Translation test failed: {str(e)}")
    
    def test_dubbing_process(self, job_id):
        """Test the complete dubbing process"""
        if not job_id:
            self.log_test("Dubbing Process", False, "No job_id provided for dubbing test")
            return
        
        try:
            # Start dubbing process
            response = self.session.post(f"{BASE_URL}/process-dubbing/{job_id}", timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                self.log_test("Dubbing Process Start", True, "Dubbing process started successfully", result)
                
                # Monitor progress
                max_wait_time = 120  # 2 minutes max wait
                start_time = time.time()
                
                while time.time() - start_time < max_wait_time:
                    status_response = self.session.get(f"{BASE_URL}/job-status/{job_id}", timeout=TEST_TIMEOUT)
                    
                    if status_response.status_code == 200:
                        job_status = status_response.json()
                        current_status = job_status.get('status')
                        progress = job_status.get('progress', 0)
                        
                        print(f"   Progress: {progress}% - Status: {current_status}")
                        
                        if current_status == 'completed':
                            self.log_test("Dubbing Process Complete", True, "Dubbing completed successfully", job_status)
                            return True
                        elif current_status == 'error':
                            error_msg = job_status.get('error_message', 'Unknown error')
                            self.log_test("Dubbing Process Complete", False, f"Dubbing failed with error: {error_msg}", job_status)
                            return False
                    
                    time.sleep(5)  # Wait 5 seconds before checking again
                
                self.log_test("Dubbing Process Complete", False, "Dubbing process timed out")
                return False
                
            else:
                self.log_test("Dubbing Process Start", False, f"Failed to start dubbing process: {response.status_code}", 
                            {"status_code": response.status_code, "response": response.text})
                return False
                
        except Exception as e:
            self.log_test("Dubbing Process", False, f"Dubbing process test failed: {str(e)}")
            return False
    
    def test_download_endpoint(self, job_id):
        """Test download endpoint for completed job"""
        if not job_id:
            self.log_test("Download Endpoint", False, "No job_id provided for download test")
            return
        
        try:
            response = self.session.get(f"{BASE_URL}/download/{job_id}", timeout=TEST_TIMEOUT)
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                if 'video' in content_type or 'application/octet-stream' in content_type:
                    self.log_test("Download Endpoint", True, "Download endpoint working correctly")
                else:
                    self.log_test("Download Endpoint", False, f"Unexpected content type: {content_type}")
            elif response.status_code == 404:
                self.log_test("Download Endpoint", False, "Download failed - job not completed or file not found")
            else:
                self.log_test("Download Endpoint", False, f"Download failed with status {response.status_code}")
                
        except Exception as e:
            self.log_test("Download Endpoint", False, f"Download test failed: {str(e)}")
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting AI Video Dubbing System Backend Tests")
        print("=" * 60)
        
        # Test 1: Health check
        self.test_health_endpoint()
        
        # Test 2: Video upload
        job_id = self.test_video_upload()
        
        # Test 3: Invalid file upload
        self.test_invalid_file_upload()
        
        # Test 4: Job status
        self.test_job_status(job_id)
        
        # Test 5: Non-existent job status
        self.test_nonexistent_job_status()
        
        # Test 6: All jobs
        self.test_all_jobs()
        
        # Test 7: Translation endpoint
        self.test_translation_endpoint()
        
        # Test 8: Complete dubbing process (this is the main test)
        if job_id:
            dubbing_success = self.test_dubbing_process(job_id)
            
            # Test 9: Download endpoint (only if dubbing succeeded)
            if dubbing_success:
                self.test_download_endpoint(job_id)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results.values() if result['success'])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        print("\n📋 DETAILED RESULTS:")
        for test_name, result in self.test_results.items():
            status = "✅" if result['success'] else "❌"
            print(f"{status} {test_name}: {result['message']}")
        
        # Print failed tests details
        failed_tests = {name: result for name, result in self.test_results.items() if not result['success']}
        if failed_tests:
            print("\n🔍 FAILED TEST DETAILS:")
            for test_name, result in failed_tests.items():
                print(f"❌ {test_name}:")
                print(f"   Error: {result['message']}")
                if result['details']:
                    print(f"   Details: {result['details']}")

if __name__ == "__main__":
    tester = VideodubbingTester()
    tester.run_all_tests()