# How to Run Lecture Extraction System

## Quick Setup

### 1. Install Dependencies

**Windows PowerShell:**
```powershell
cd lecture_extraction_system
.\setup.bat
```

**Or manually:**
```powershell
py -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

**Command Prompt (CMD):**
```cmd
cd lecture_extraction_system
setup.bat
```

### 2. Setup Google Colab
- Open https://colab.research.google.com/
- Create new notebook with **GPU** runtime
- Upload `colab_server.ipynb` from this folder
- Add your ngrok token in Cell 2
- Run all cells (1, 2, 3, 4)
- Copy the ngrok URL (e.g. https://xxxx.ngrok-free.dev)

Colab handles: Whisper transcription, OCR, frame extraction, and LLM. Your PC saves transcripts, frames, and audio locally.

### 3. Run Application

**Option A: Using script (Windows)**
```bash
.\run.bat
```

**Option B: Manual**
```powershell
.\venv\Scripts\activate
streamlit run app.py
```

### 4. Use the System
1. Paste Colab URL in sidebar
2. Click "Connect"
3. Upload video in Upload tab
4. Processing runs on Colab (progress shown in frontend)
5. Transcripts, frames, audio saved locally
6. Chat tab for Q&A

## Configuration

Edit `config.py` to change:
- Whisper model size (tiny/base/small/medium/large)
- Frame extraction rate
- OCR confidence threshold

## Management Commands

```powershell
# Activate venv first
.\venv\Scripts\activate

# List all lectures
python manage.py list

# View lecture details
python manage.py info <lecture_id>

# Export transcript
python manage.py export <lecture_id> -o output.txt

# Delete lecture
python manage.py delete <lecture_id>

# Show statistics
python manage.py stats

# Clean up failed lectures
python manage.py cleanup
```

## Troubleshooting

**FFmpeg not found:**
```bash
# Windows
choco install ffmpeg

# Linux
sudo apt install ffmpeg
```

**Connection failed:**
- Check Colab is running
- Verify ngrok URL is correct
- Restart Colab if timed out

**Processing slow:**
- Use smaller Whisper model (tiny or base)
- Reduce frame extraction rate in config.py

That's it! Enjoy your lecture extraction system.
