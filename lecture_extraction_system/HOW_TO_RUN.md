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

### 2. Setup Google Colab LLM
- Open https://colab.research.google.com/
- Create new notebook with GPU runtime
- Run these cells:

```python
# Install packages
!pip install flask pyngrok transformers torch accelerate bitsandbytes

# Setup ngrok (get token from https://dashboard.ngrok.com/)
from pyngrok import ngrok
ngrok.set_auth_token("YOUR_TOKEN")

# Copy content from colab_server_example.py and run
start_server()
```

- Copy the ngrok URL (https://xxxx.ngrok.io)

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
1. Paste Colab URL in sidebar settings
2. Click "Test Connection"
3. Upload lecture video
4. Wait for processing
5. Ask questions in Chat tab

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
