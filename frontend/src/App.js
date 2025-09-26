import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [file, setFile] = useState(null);
  const [sourceLanguage, setSourceLanguage] = useState('english');
  const [targetLanguage, setTargetLanguage] = useState('hindi');
  const [jobs, setJobs] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState({});
  const [dragActive, setDragActive] = useState(false);

  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 3000); // Poll every 3 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchJobs = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/jobs`);
      if (response.ok) {
        const jobsData = await response.json();
        setJobs(jobsData);
      }
    } catch (error) {
      console.error('Error fetching jobs:', error);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      alert('Please select a video file');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('source_language', sourceLanguage);
    formData.append('target_language', targetLanguage);

    try {
      const response = await fetch(`${BACKEND_URL}/api/upload-video`, {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const result = await response.json();
        alert('Video uploaded successfully!');
        setFile(null);
        fetchJobs();
      } else {
        const error = await response.json();
        alert(`Upload failed: ${error.detail}`);
      }
    } catch (error) {
      alert(`Upload error: ${error.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleProcess = async (jobId) => {
    setProcessing(prev => ({ ...prev, [jobId]: true }));
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/process-dubbing/${jobId}`, {
        method: 'POST',
      });

      if (response.ok) {
        alert('Dubbing process started!');
        fetchJobs();
      } else {
        const error = await response.json();
        alert(`Processing failed: ${error.detail}`);
      }
    } catch (error) {
      alert(`Processing error: ${error.message}`);
    } finally {
      setProcessing(prev => ({ ...prev, [jobId]: false }));
    }
  };

  const handleDownload = async (jobId, filename) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/download/${jobId}`);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `${filename}_dubbed.mp4`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
      } else {
        alert('Download failed');
      }
    } catch (error) {
      alert(`Download error: ${error.message}`);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'text-green-600';
      case 'error': return 'text-red-600';
      case 'uploaded': return 'text-blue-600';
      default: return 'text-yellow-600';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed': return '✅';
      case 'error': return '❌';
      case 'uploaded': return '📁';
      default: return '⏳';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900">
      {/* Header */}
      <div className="bg-black/20 backdrop-blur-sm border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="bg-gradient-to-r from-cyan-400 to-purple-500 p-3 rounded-2xl">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </div>
              <div>
                <h1 className="text-3xl font-bold text-white">AI Video Dubbing</h1>
                <p className="text-blue-200">Advanced voice cloning & emotion preservation</p>
              </div>
            </div>
            <div className="hidden md:flex items-center space-x-4 text-sm text-blue-200">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                <span>AI Ready</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
          {/* Upload Section */}
          <div className="xl:col-span-1">
            <div className="bg-white/10 backdrop-blur-md rounded-3xl p-8 border border-white/20 shadow-2xl">
              <h2 className="text-2xl font-bold text-white mb-6 flex items-center">
                <span className="bg-gradient-to-r from-cyan-400 to-purple-500 p-2 rounded-xl mr-3">
                  🎬
                </span>
                Upload Video
              </h2>

              {/* File Upload Area */}
              <div
                className={`relative border-2 border-dashed rounded-2xl p-8 text-center transition-all duration-300 ${
                  dragActive
                    ? 'border-cyan-400 bg-cyan-400/10'
                    : 'border-white/30 hover:border-white/50'
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                <input
                  type="file"
                  accept=".mp4,.avi,.mov,.mkv"
                  onChange={handleFileChange}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />
                
                <div className="flex flex-col items-center space-y-4">
                  <div className="bg-gradient-to-r from-cyan-400 to-purple-500 p-4 rounded-2xl">
                    <svg className="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                  </div>
                  
                  {file ? (
                    <div className="text-white">
                      <p className="font-semibold">{file.name}</p>
                      <p className="text-sm text-blue-200">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                    </div>
                  ) : (
                    <div className="text-white">
                      <p className="text-lg font-semibold">Drop your video here</p>
                      <p className="text-sm text-blue-200">or click to browse</p>
                      <p className="text-xs text-blue-300 mt-2">Supports MP4, AVI, MOV, MKV</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Language Selection */}
              <div className="grid grid-cols-2 gap-4 mt-6">
                <div>
                  <label className="block text-sm font-medium text-blue-200 mb-2">From</label>
                  <select
                    value={sourceLanguage}
                    onChange={(e) => setSourceLanguage(e.target.value)}
                    className="w-full bg-white/10 border border-white/30 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:border-transparent"
                  >
                    <option value="english">🇺🇸 English</option>
                    <option value="hindi">🇮🇳 Hindi</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-blue-200 mb-2">To</label>
                  <select
                    value={targetLanguage}
                    onChange={(e) => setTargetLanguage(e.target.value)}
                    className="w-full bg-white/10 border border-white/30 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:border-transparent"
                  >
                    <option value="hindi">🇮🇳 Hindi</option>
                    <option value="english">🇺🇸 English</option>
                  </select>
                </div>
              </div>

              {/* Upload Button */}
              <button
                onClick={handleUpload}
                disabled={!file || uploading}
                className={`w-full mt-6 py-4 px-6 rounded-2xl font-semibold text-white transition-all duration-300 ${
                  !file || uploading
                    ? 'bg-gray-600 cursor-not-allowed'
                    : 'bg-gradient-to-r from-cyan-500 to-purple-600 hover:from-cyan-600 hover:to-purple-700 shadow-lg hover:shadow-xl transform hover:scale-105'
                }`}
              >
                {uploading ? (
                  <div className="flex items-center justify-center space-x-2">
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    <span>Uploading...</span>
                  </div>
                ) : (
                  'Upload & Queue for Dubbing'
                )}
              </button>
            </div>

            {/* Features */}
            <div className="mt-6 bg-white/5 backdrop-blur-sm rounded-2xl p-6 border border-white/10">
              <h3 className="text-lg font-semibold text-white mb-4">🚀 AI Features</h3>
              <div className="space-y-3 text-sm">
                <div className="flex items-center space-x-3 text-blue-200">
                  <span className="text-green-400">✓</span>
                  <span>Voice cloning & preservation</span>
                </div>
                <div className="flex items-center space-x-3 text-blue-200">
                  <span className="text-green-400">✓</span>
                  <span>Emotion & intensity transfer</span>
                </div>
                <div className="flex items-center space-x-3 text-blue-200">
                  <span className="text-green-400">✓</span>
                  <span>Cultural context adaptation</span>
                </div>
                <div className="flex items-center space-x-3 text-blue-200">
                  <span className="text-green-400">✓</span>
                  <span>Perfect lip-sync timing</span>
                </div>
              </div>
            </div>
          </div>

          {/* Jobs Section */}
          <div className="xl:col-span-2">
            <div className="bg-white/10 backdrop-blur-md rounded-3xl p-8 border border-white/20 shadow-2xl">
              <h2 className="text-2xl font-bold text-white mb-6 flex items-center justify-between">
                <div className="flex items-center">
                  <span className="bg-gradient-to-r from-cyan-400 to-purple-500 p-2 rounded-xl mr-3">
                    📊
                  </span>
                  Dubbing Jobs
                </div>
                <span className="text-sm text-blue-300 bg-white/10 px-3 py-1 rounded-full">
                  {jobs.length} total
                </span>
              </h2>

              {jobs.length === 0 ? (
                <div className="text-center py-12">
                  <div className="bg-white/5 rounded-full p-8 w-24 h-24 mx-auto mb-4 flex items-center justify-center">
                    <span className="text-4xl">🎵</span>
                  </div>
                  <p className="text-white text-lg font-medium">No dubbing jobs yet</p>
                  <p className="text-blue-300 text-sm mt-2">Upload a video to get started</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {jobs.map((job) => (
                    <div key={job.id} className="bg-white/5 rounded-2xl p-6 border border-white/10 hover:border-white/20 transition-all duration-300">
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center space-x-3">
                          <span className="text-2xl">{getStatusIcon(job.status)}</span>
                          <div>
                            <h3 className="text-white font-semibold">{job.filename}</h3>
                            <p className="text-sm text-blue-300">
                              {job.original_language} → {job.target_language}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className={`font-semibold capitalize ${getStatusColor(job.status)}`}>
                            {job.status}
                          </p>
                          <p className="text-xs text-blue-300">
                            {new Date(job.created_at).toLocaleDateString()}
                          </p>
                        </div>
                      </div>

                      {/* Progress Bar */}
                      {job.progress > 0 && job.progress < 100 && (
                        <div className="mb-4">
                          <div className="flex justify-between text-sm text-blue-300 mb-1">
                            <span>Progress</span>
                            <span>{job.progress}%</span>
                          </div>
                          <div className="w-full bg-white/10 rounded-full h-2">
                            <div 
                              className="bg-gradient-to-r from-cyan-400 to-purple-500 h-2 rounded-full transition-all duration-300"
                              style={{ width: `${job.progress}%` }}
                            ></div>
                          </div>
                        </div>
                      )}

                      {/* Error Message */}
                      {job.error_message && (
                        <div className="mb-4 p-3 bg-red-500/20 border border-red-500/30 rounded-lg">
                          <p className="text-red-300 text-sm">{job.error_message}</p>
                        </div>
                      )}

                      {/* Action Buttons */}
                      <div className="flex space-x-3">
                        {job.status === 'uploaded' && (
                          <button
                            onClick={() => handleProcess(job.id)}
                            disabled={processing[job.id]}
                            className="flex-1 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white py-2 px-4 rounded-xl font-medium transition-all duration-300 disabled:opacity-50"
                          >
                            {processing[job.id] ? 'Starting...' : 'Start Dubbing'}
                          </button>
                        )}
                        
                        {job.status === 'completed' && (
                          <button
                            onClick={() => handleDownload(job.id, job.filename)}
                            className="flex-1 bg-gradient-to-r from-blue-500 to-cyan-600 hover:from-blue-600 hover:to-cyan-700 text-white py-2 px-4 rounded-xl font-medium transition-all duration-300"
                          >
                            Download Dubbed Video
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;