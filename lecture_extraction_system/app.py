from flask import Flask, request, jsonify
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import cv2
import whisper
import easyocr
import subprocess
import os
import tempfile
import uuid
import threading
import numpy as np
import chromadb
from sentence_transformers import SentenceTransformer

app = Flask(__name__)
model = None
tokenizer = None
embedder = None
chroma_client = None
jobs = {}
FRAME_RATE = 30

# =============================
# CHUNKING HELPER
# =============================
def chunk_text(text, chunk_size=300, overlap=50):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks

# =============================
# VIDEO PROCESSING
# =============================
def process_video_task(job_id, video_path):
    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 10
        jobs[job_id]["message"] = "Extracting audio..."

        audio_path = video_path.replace(".mp4", ".wav").replace(".avi", ".wav").replace(".mov", ".wav").replace(".mkv", ".wav")
        subprocess.run(["ffmpeg", "-i", video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", "-y", audio_path],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        jobs[job_id]["progress"] = 25
        jobs[job_id]["message"] = "Transcribing with Whisper..."

        whisper_model = whisper.load_model("base")
        result = whisper_model.transcribe(audio_path, verbose=False)
        segments = result.get("segments", [])
        transcript = [{"start": s["start"], "end": s["end"], "text": s.get("text", "").strip(), "confidence": 0.0} for s in segments]
        duration = segments[-1]["end"] if segments else 0
        full_transcript_text = " ".join([s["text"] for s in transcript])

        jobs[job_id]["progress"] = 50
        jobs[job_id]["message"] = "Extracting frames..."

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frames_data = []
        frame_count = 0
        saved = 0
        ocr_reader = easyocr.Reader(["en"], gpu=True)
        all_ocr_text = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_count % FRAME_RATE == 0:
                timestamp = frame_count / fps
                results = ocr_reader.readtext(frame)
                printed_text = []
                for (bbox, text, conf) in results:
                    if conf >= 0.5:
                        printed_text.append(text)
                joined = " ".join(printed_text)
                all_ocr_text.append(joined)
                frames_data.append({
                    "timestamp": timestamp,
                    "printed_text": joined,
                    "handwritten_text": "",
                    "ocr_confidence": 0.0
                })
                saved += 1
                if saved % 10 == 0:
                    jobs[job_id]["progress"] = 50 + int(40 * saved / max(1, int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / FRAME_RATE)))
                    jobs[job_id]["message"] = f"OCR on frames... {saved} done"
            frame_count += 1
        cap.release()

        jobs[job_id]["progress"] = 90
        jobs[job_id]["message"] = "Building RAG index..."

        # Combine transcript and OCR text
        combined_text = full_transcript_text + " " + " ".join(all_ocr_text)

        # Chunk the combined text
        chunks = chunk_text(combined_text, chunk_size=300, overlap=50)

        # Embed and store in ChromaDB
        collection_name = f"job_{job_id}"
        collection = chroma_client.create_collection(name=collection_name)

        batch_size = 50
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            embeddings = embedder.encode(batch).tolist()
            collection.add(
                documents=batch,
                embeddings=embeddings,
                ids=[f"chunk_{i + j}" for j in range(len(batch))]
            )

        jobs[job_id]["progress"] = 95
        jobs[job_id]["message"] = "Finalizing..."

        jobs[job_id]["result"] = {
            "transcript": transcript,
            "frames": frames_data,
            "duration": duration,
            "chunks_indexed": len(chunks)
        }
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["message"] = "Done"

        os.remove(video_path)
        if os.path.exists(audio_path):
            os.remove(audio_path)

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["message"] = str(e)

# =============================
# ROUTES
# =============================

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "model_loaded": model is not None}), 200

@app.route('/upload', methods=['POST'])
def upload_video():
    try:
        if 'video' not in request.files:
            return jsonify({"error": "No video file"}), 400
        file = request.files['video']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        job_id = str(uuid.uuid4())
        video_path = os.path.join(tempfile.gettempdir(), f"{job_id}_{file.filename}")
        file.save(video_path)
        jobs[job_id] = {"status": "processing", "progress": 0, "message": "Starting...", "result": None, "error": None}
        threading.Thread(target=process_video_task, args=(job_id, video_path)).start()
        return jsonify({"job_id": job_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404
    j = jobs[job_id]
    return jsonify({"status": j["status"], "progress": j["progress"], "message": j["message"], "error": j.get("error")}), 200

@app.route('/result/<job_id>', methods=['GET'])
def get_result(job_id):
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404
    if jobs[job_id]["status"] != "completed":
        return jsonify({"error": "Job not ready"}), 400
    return jsonify(jobs[job_id]["result"]), 200

@app.route('/job/<job_id>', methods=['DELETE'])
def delete_job(job_id):
    try:
        collection_name = f"job_{job_id}"
        chroma_client.delete_collection(name=collection_name)
        if job_id in jobs:
            del jobs[job_id]
        return jsonify({"ok": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.json
        prompt = data.get('prompt', '')
        job_id = data.get('job_id', '')
        max_tokens = data.get('max_tokens', 500)
        temperature = data.get('temperature', 0.7)

        # RAG - retrieve relevant chunks from ChromaDB
        context = ""
        if job_id:
            try:
                collection_name = f"job_{job_id}"
                collection = chroma_client.get_collection(name=collection_name)
                question_embedding = embedder.encode([prompt]).tolist()
                results = collection.query(
                    query_embeddings=question_embedding,
                    n_results=5
                )
                retrieved_chunks = results["documents"][0]
                context = "\n\n".join(retrieved_chunks)
            except Exception as e:
                return jsonify({"error": f"RAG retrieval failed: {str(e)}. Ensure the lecture was uploaded and indexing completed."}), 400
        else:
            context = data.get('context', '')

        # Truncate context just in case
        if len(context) > 6000:
            context = context[:6000] + "\n\n[Context truncated...]"

        full_prompt = f"""<s>[INST] Based on the following lecture content, answer the question.

Lecture Content:
{context}

Question: {prompt} [/INST]"""

        inputs = tokenizer(full_prompt, return_tensors="pt", truncation=True, max_length=4096).to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
            )

        prompt_len = inputs["input_ids"].shape[1]
        generated_ids = outputs[0][prompt_len:]
        answer = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()

        return jsonify({
            "text": answer,
            "metadata": {
                "prompt_length": len(full_prompt),
                "tokens_generated": len(outputs[0]) - len(inputs['input_ids'][0]),
                "rag_used": bool(job_id)
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =============================
# LOAD MODELS
# =============================
def load_llm():
    global model, tokenizer, embedder, chroma_client

    # Load sentence embedder for RAG
    print("Loading sentence embedder...")
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    print("Embedder loaded.")

    # Init ChromaDB in memory
    print("Initializing ChromaDB...")
    chroma_client = chromadb.Client()
    print("ChromaDB ready.")

    # Load Mistral 7B in 4-bit
    model_name = "mistralai/Mistral-7B-Instruct-v0.2"
    print(f"Loading model: {model_name}")

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True
    )

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=quant_config,
        device_map="auto"
    )

    print("Mistral 7B loaded successfully!")

def start_server():
    load_llm()
    from pyngrok import ngrok
    public_url = ngrok.connect(5000)
    print(f"\n🚀 Server is running!")
    print(f"📡 Public URL: {public_url}")
    print(f"Copy this URL to your local app\n")
    app.run(port=5000)

if __name__ == "__main__":
    start_server()
