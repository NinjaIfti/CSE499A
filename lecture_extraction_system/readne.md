📚 Lecture Extraction & Analysis System
🎯 Project Overview
An intelligent lecture video processing system that extracts multimodal content (audio, slides, board writing) from lecture recordings and uses a local LLM to synthesize coherent study notes. The system features a web-based UI for video upload, automated processing, and interactive Q&A capabilities.

🏗️ System Architecture
┌─────────────────────────────────────────────────────────┐
│                    User Interface                        │
│              (Streamlit Web Application)                 │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                  Backend Pipeline                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │ 1. Video Upload & Storage                        │  │
│  └──────────────┬───────────────────────────────────┘  │
│                 │                                        │
│  ┌──────────────▼───────────────────────────────────┐  │
│  │ 2. Audio Extraction (FFmpeg)                     │  │
│  │    → Whisper AI: Speech-to-Text with timestamps  │  │
│  └──────────────┬───────────────────────────────────┘  │
│                 │                                        │
│  ┌──────────────▼───────────────────────────────────┐  │
│  │ 3. Frame Extraction (OpenCV)                     │  │
│  │    → Every 5 seconds                             │  │
│  └──────────────┬───────────────────────────────────┘  │
│                 │                                        │
│  ┌──────────────▼───────────────────────────────────┐  │
│  │ 4. Frame Classification                          │  │
│  │    → Brightness-based: Slide vs Board           │  │
│  └──────────────┬───────────────────────────────────┘  │
│                 │                                        │
│  ┌──────────────▼───────────────────────────────────┐  │
│  │ 5. OCR Processing (EasyOCR)                      │  │
│  │    → Extract text from slides/board              │  │
│  │    → Confidence scoring                          │  │
│  └──────────────┬───────────────────────────────────┘  │
│                 │                                        │
│  ┌──────────────▼───────────────────────────────────┐  │
│  │ 6. LLM Synthesis (Local Llama 3.1 8B)           │  │
│  │    → Temporal alignment                          │  │
│  │    → Semantic integration                        │  │
│  │    → Coherent note generation                    │  │
│  └──────────────┬───────────────────────────────────┘  │
└─────────────────┼───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│            SQLite Database                          │
│  - Lecture metadata                                 │
│  - Extracted transcripts                            │
│  - OCR results                                      │
│  - Generated notes                                  │
└─────────────────────────────────────────────────────┘

🔑 Key Features
1. Multimodal Extraction

Audio: Speech-to-text transcription with precise timestamps
Slides: OCR text extraction from projected presentations
Board: Handwritten content detection from whiteboards/blackboards

2. Intelligent Classification

Automatic distinction between slide frames (bright, printed) and board frames (dark, handwritten)
Brightness-based heuristic: threshold at 150/255 grayscale value

3. Local LLM Processing

Runs Llama 3.1 8B locally (no cloud API required)
Privacy-preserving: all data stays on your machine
Customizable prompts for different analysis tasks

4. Interactive Web Interface

Upload & Process: Drag-and-drop video upload with real-time progress
View Past Lectures: Browse and reload previously processed videos
Interactive Q&A: Ask questions, explain specific sections, custom prompts

5. Persistent Storage

SQLite database stores all processed lectures
Enables reloading and re-querying without reprocessing


📁 Project Structure
lecture_extraction_system/
│
├── README.md                     # This file
├── requirements.txt              # Python dependencies
├── app.py                        # Main Streamlit application
│
├── backend/                      # Core processing modules
│   ├── __init__.py
│   ├── video_processor.py        # Video/audio extraction, Whisper transcription
│   ├── ocr_processor.py          # Frame classification, OCR text extraction
│   ├── llm_handler.py            # Local LLM interface (Llama 3.1)
│   └── database.py               # SQLite database operations
│
├── uploads/                      # User-uploaded video files (gitignored)
├── outputs/                      # Processed frames and results (gitignored)
├── frames/                       # Extracted video frames (gitignored)
├── models/                       # Downloaded LLM models (gitignored)
│
├── lectures.db                   # SQLite database (created on first run)
└── temp_audio.wav                # Temporary audio file (gitignored)

🛠️ Technology Stack
ComponentTechnologyPurposeFrontendStreamlitWeb-based UI for user interactionVideo ProcessingFFmpeg, OpenCVAudio extraction, frame samplingSpeech RecognitionOpenAI Whisper (base model)Audio transcription with timestampsOCREasyOCRText extraction from imagesLLMLlama 3.1 8B (4-bit quantized)Local text synthesis and Q&ADatabaseSQLite + SQLAlchemyPersistent lecture storageML FrameworkPyTorch, TransformersModel loading and inference

🚀 Installation & Setup
Prerequisites

Python 3.9+
CUDA-compatible GPU (recommended, 8GB+ VRAM)
16GB+ RAM
FFmpeg installed on system

Step 1: Clone/Create Project
bashmkdir lecture_extraction_system
cd lecture_extraction_system
Step 2: Create Virtual Environment
bashpython -m venv venv

# Activate:
# Linux/Mac:
source venv/bin/activate

# Windows:
venv\Scripts\activate
Step 3: Install Dependencies
bashpip install -r requirements.txt
```

**`requirements.txt` contents:**
```
streamlit==1.32.0
openai-whisper==20231117
opencv-python==4.9.0
easyocr==1.7.0
torch==2.2.0
transformers==4.38.0
accelerate==0.27.0
bitsandbytes==0.42.0
sqlalchemy==2.0.25
pillow==10.2.0
numpy==1.26.4
pandas==2.2.0
Step 4: Install FFmpeg
Ubuntu/Debian:
bashsudo apt-get update
sudo apt-get install ffmpeg
macOS:
bashbrew install ffmpeg
Windows:

Download from ffmpeg.org
Add to PATH

Step 5: Download LLM Model (First Run)
The Llama 3.1 8B model will auto-download (~5GB) on first use. This requires:

HuggingFace account
Accept Llama license at meta-llama/Llama-3.1-8B-Instruct
Login via CLI:

bashpip install huggingface-hub
huggingface-cli login
# Paste your HF token
Step 6: Run Application
bashstreamlit run app.py
The app will open at http://localhost:8501

📖 Usage Guide
Mode 1: Upload & Process

Click "📤 Upload & Process" in sidebar
Upload a video file (.mp4, .avi, .mov, .mkv)
Click "🚀 Start Processing"
Wait for 5-step pipeline:

Step 1: Audio extraction (~10s)
Step 2: Transcription (~1-2 min for 5-min video)
Step 3: Frame extraction (~5s)
Step 4: OCR processing (~30-60s)
Step 5: LLM synthesis (~30-60s)


View generated notes
Download as .txt file

Mode 2: View Past Lectures

Click "📚 View Past Lectures"
Browse all processed videos
Click "Load Lecture #X" to view notes
Lecture becomes available for Q&A

Mode 3: Interactive Q&A

Click "💬 Interactive Q&A"
Load a lecture first (from Mode 1 or 2)
Choose tab:

Ask Questions: Natural language queries about content
Explain Time Section: Get detailed explanation of specific timestamp range
Custom Prompt: Advanced users can write custom analysis prompts




🧠 How It Works
Audio Transcription Pipeline
python# 1. Extract audio from video
FFmpeg: video.mp4 → audio.wav (16kHz mono)

# 2. Transcribe with Whisper
Whisper(audio.wav) → [
    {start: 0.0, end: 4.2, text: "Today we'll discuss..."},
    {start: 4.2, end: 8.5, text: "The key concept is..."},
    ...
]
OCR Pipeline
python# 1. Extract frames
OpenCV: video.mp4 → [frame_0.jpg, frame_5s.jpg, frame_10s.jpg, ...]

# 2. Classify each frame
for frame in frames:
    brightness = mean_pixel_value(frame)
    if brightness > 150:
        type = "slide"  # Bright projector
    else:
        type = "board"  # Dark whiteboard

# 3. Extract text
EasyOCR(frame) → {
    text: "f(x) = x²",
    confidence: 0.87,
    bounding_boxes: [...]
}
LLM Synthesis Process
python# 1. Combine all data sources
prompt = f"""
Create lecture notes from:

AUDIO TRANSCRIPT:
[0.0s - 4.2s]: "Today we'll discuss derivatives"
[4.2s - 8.5s]: "The key concept is rate of change"

SLIDE CONTENT:
[5.0s]: "Chapter 3: Derivatives"
[10.0s]: "f(x) = x²"

BOARD WRITING:
[15.0s]: "f'(x) = 2x"

Task: Synthesize into coherent study notes.
"""

# 2. LLM processes
Llama 3.1:
  - Identifies temporal relationships (audio at 4.2s + slide at 5.0s = same topic)
  - Removes redundancy (both mention "derivatives")
  - Adds context and flow
  - Structures with headers

# 3. Output
"""
Chapter 3: Derivatives

Introduction
In this lecture, we explore derivatives and their meaning as rates of change.

Example
Consider the function f(x) = x². Its derivative is f'(x) = 2x, which tells us...
"""

🎯 LLM Capabilities
1. Automatic Note Generation

Synthesizes audio, slides, and board into unified notes
Maintains logical flow and structure
Includes formulas, definitions, examples

2. Question Answering
pythonUser: "What is the derivative of x²?"
LLM: Searches lecture content → "The derivative of f(x) = x² is f'(x) = 2x"
3. Section Explanation
pythonUser: "Explain what happened between 45s and 90s"
LLM: Filters data for that timeframe → Generates detailed explanation
4. Custom Analysis
pythonUser: "List all formulas mentioned in this lecture"
LLM: Extracts and formats all mathematical expressions

🔧 Configuration Options
Adjust Frame Extraction Rate
In backend/video_processor.py:
pythondef extract_frames(self, video_path, interval_seconds=5):  # Change this

Lower = more frames, better coverage, slower processing
Higher = fewer frames, faster processing, might miss content

Change LLM Model
In backend/llm_handler.py:
pythondef __init__(self, model_name="meta-llama/Llama-3.1-8B-Instruct"):
Alternative models:

"mistralai/Mistral-7B-Instruct-v0.2" - Faster, less capable
"google/gemma-2-9b-it" - Google's model
"meta-llama/Llama-3.1-70B-Instruct" - More capable, needs 40GB+ VRAM

Adjust Classification Threshold
In backend/ocr_processor.py:
pythonreturn "slide" if mean_brightness > 150 else "board"  # Change 150

Higher threshold = fewer slides detected
Lower threshold = more slides detected


📊 Performance Benchmarks
Test video: 5-minute lecture (300 seconds)
StepTimeResource UsageAudio extraction10sCPU onlyWhisper transcription60-90sGPU: 2GB VRAMFrame extraction5sCPU onlyOCR (60 frames)30-45sGPU: 3GB VRAMLLM synthesis30-60sGPU: 6GB VRAMTotal~3-5 minPeak: 8GB VRAM
Note: First run takes longer due to model downloads.

🐛 Troubleshooting
Issue: "CUDA out of memory"
Solution 1: Use CPU-only mode
python# In backend/ocr_processor.py
self.reader = easyocr.Reader(['en'], gpu=False)

# In backend/llm_handler.py
device_map="cpu"
Solution 2: Use smaller LLM
pythonmodel_name = "microsoft/Phi-3-mini-4k-instruct"  # Only 3.8B params
Issue: "FFmpeg not found"
Solution: Install FFmpeg and add to PATH
bash# Verify installation
ffmpeg -version
Issue: OCR confidence very low (<0.5)
Causes:

Blurry video
Small text
Poor lighting

Solutions:

Increase frame extraction interval (capture clearer frames)
Pre-process frames (sharpen, contrast adjustment)
Use higher resolution video source

Issue: LLM generating irrelevant content
Solution: Improve prompt engineering
python# Add more specific instructions
prompt = f"""You are a teaching assistant. Be concise and factual.
Only use information from the lecture data provided. Do not add external knowledge.

{data}
"""
```

---

## 🔐 Privacy & Security

### Data Privacy
- ✅ **All processing happens locally** - no data sent to external servers
- ✅ **No API calls** - LLM runs on your machine
- ✅ **SQLite database** - stored locally in project folder

### Sensitive Content
- Videos remain in `uploads/` folder (add to `.gitignore`)
- Database contains all extracted text (keep `lectures.db` private)

---

## 🚧 Known Limitations

1. **Handwriting OCR**: Accuracy ~70-85% (vs 95%+ for printed text)
2. **Classification**: Simple brightness-based method may fail with:
   - Dark slides with black backgrounds
   - Bright whiteboards with strong lighting
3. **Mathematical Notation**: OCR may misread complex formulas (∫, ∑, etc.)
4. **Speaker Diarization**: Doesn't distinguish between multiple speakers
5. **Language**: Currently English-only (configurable in code)

---

## 🎓 Academic Context

### Problem Statement
Manually creating study notes from recorded lectures is time-consuming and error-prone. Students must:
1. Watch entire video
2. Transcribe audio
3. Screenshot/type slide content
4. Copy board writing
5. Integrate all sources into coherent notes

### Solution Approach
Automate the extraction and synthesis pipeline using:
- **Computer Vision** (frame classification, OCR)
- **Speech Recognition** (Whisper)
- **Natural Language Processing** (LLM synthesis)

### Technical Challenges Addressed

#### 1. Temporal Alignment
**Problem:** Audio and visual content are asynchronous
```
Audio: "This formula is important" (t=10s)
Slide: Shows "f(x) = x²" (t=12s)
Solution: LLM uses timestamps to align related content
2. Multimodal Integration
Problem: Three disconnected data streams
Solution: LLM semantic understanding to merge related information
3. Redundancy Removal
Problem: Same concept repeated in audio, slides, board
Solution: LLM identifies duplicates and consolidates
4. Context Enhancement
Problem: Visual formulas lack verbal explanation
Solution: LLM adds context from audio to explain visual content

🔬 Future Enhancements
Short-term (Easy)

 Export to PDF/DOCX formats
 Support for additional languages
 Better handwriting recognition (TrOCR model)
 Video player with synchronized transcript

Medium-term (Moderate)

 Speaker diarization (distinguish professor vs student questions)
 Automatic summarization levels (brief/detailed/comprehensive)
 Flashcard generation from content
 Quiz question generation

Long-term (Advanced)

 Real-time processing (live lecture streaming)
 Multi-camera support (switch between slides and board)
 Gesture recognition (pointing at specific slide elements)
 Integration with LMS (Canvas, Moodle, Blackboard)


📚 References & Citations
Models Used

Whisper: Radford et al. (2022) - Robust Speech Recognition via Large-Scale Weak Supervision
Llama 3.1: Meta AI (2024) - The Llama 3 Herd of Models
EasyOCR: JaidedAI - GitHub Repository

Libraries

OpenCV: opencv.org
Streamlit: streamlit.io
HuggingFace Transformers: huggingface.co/docs/transformers


🤝 Contributing
This is an academic project. For improvements:

Bug Reports: Document issue with error logs
Feature Requests: Explain use case and benefits
Code Contributions: Follow existing architecture patterns


📄 License
This project is for educational purposes. Please respect licenses of:

OpenAI Whisper (MIT)
Meta Llama 3.1 (Meta License)
EasyOCR (Apache 2.0)


👤 Author
Project: Multimodal Lecture Extraction System
Purpose: Academic project for automated lecture note generation
Date: 2025

📞 Support
For questions about implementation:

Check "Troubleshooting" section above
Review code comments in backend/ modules
Consult individual library documentation


🎯 Quick Start Checklist

 Python 3.9+ installed
 CUDA-compatible GPU available (optional but recommended)
 FFmpeg installed and in PATH
 Virtual environment created
 Dependencies installed (pip install -r requirements.txt)
 HuggingFace CLI login completed
 Llama 3.1 license accepted on HuggingFace
 streamlit run app.py launches successfully
 Test video uploaded and processed


🎓 Ready to process your first lecture? Run streamlit run app.py and upload a video!