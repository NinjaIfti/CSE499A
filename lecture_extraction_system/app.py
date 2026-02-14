import streamlit as st
import html
from pathlib import Path
from datetime import datetime
import time

from database import init_database, SessionLocal, Lecture, Transcript, Frame, Query, Chat, ChatMessage
from lecture_processor import LectureProcessor
from llm_client import LLMClient
from video_processor import VideoProcessor
from config import UPLOAD_DIR, PROCESSED_DIR, MAX_VIDEO_SIZE_MB

st.set_page_config(
    page_title="Lecture AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .chat-msg { padding: 1rem; border-radius: 10px; margin-bottom: 1rem; }
    .chat-user { background: #f1f5f9; border-left: 4px solid #6366f1; }
    .chat-assistant { background: #f8fafc; border-left: 4px solid #10b981; }
    .summary-box { background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%); padding: 1.25rem; border-radius: 12px; margin: 1rem 0; border: 1px solid #a7f3d0; }
    .content-block { padding: 0.75rem; margin: 0.5rem 0; border-radius: 8px; font-size: 0.9rem; }
    .event-speech { background: #eef2ff; border-left: 3px solid #6366f1; }
    .event-slide { background: #ecfdf5; border-left: 3px solid #10b981; }
    .event-hand { background: #fffbeb; border-left: 3px solid #f59e0b; }
</style>
""", unsafe_allow_html=True)

init_database()

if 'llm_client' not in st.session_state:
    st.session_state.llm_client = LLMClient()
if 'api_connected' not in st.session_state:
    st.session_state.api_connected = False
def load_chats_from_db():
    db = SessionLocal()
    rows = db.query(Chat).order_by(Chat.id).all()
    out = []
    for c in rows:
        msgs = db.query(ChatMessage).filter(ChatMessage.chat_id == c.id).order_by(ChatMessage.id).all()
        out.append({
            "id": c.id,
            "lecture_id": c.lecture_id,
            "title": c.title or "New chat",
            "messages": [{"role": m.role, "content": m.content} for m in msgs],
        })
    db.close()
    return out

if 'chats' not in st.session_state:
    chats = load_chats_from_db()
    if not chats:
        db = SessionLocal()
        new_row = Chat(lecture_id=None, title="New chat")
        db.add(new_row)
        db.commit()
        new_id = new_row.id
        db.close()
        st.session_state.chats = [{"id": new_id, "lecture_id": None, "title": "New chat", "messages": []}]
    else:
        st.session_state.chats = chats
if 'active_chat_id' not in st.session_state:
    st.session_state.active_chat_id = st.session_state.chats[0]["id"]

def get_chat():
    for c in st.session_state.chats:
        if c["id"] == st.session_state.active_chat_id:
            return c
    return st.session_state.chats[0]

def save_chat_message(chat_id, role, content):
    db = SessionLocal()
    db.add(ChatMessage(chat_id=chat_id, role=role, content=content))
    db.commit()
    db.close()

def update_chat_in_db(chat_id, lecture_id=None, title=None):
    db = SessionLocal()
    row = db.query(Chat).filter(Chat.id == chat_id).first()
    if row:
        if lecture_id is not None:
            row.lecture_id = lecture_id
        if title is not None:
            row.title = title
        db.commit()
    db.close()

def new_chat():
    db = SessionLocal()
    row = Chat(lecture_id=None, title="New chat")
    db.add(row)
    db.commit()
    row_id = row.id
    db.close()
    st.session_state.chats.append({"id": row_id, "lecture_id": None, "title": "New chat", "messages": []})
    st.session_state.active_chat_id = row_id

def sidebar():
    with st.sidebar:
        st.markdown("### API")
        api_url = st.text_input("Colab URL", value=st.session_state.llm_client.api_url, placeholder="https://xxx.ngrok.io", label_visibility="collapsed")
        if st.button("Connect", use_container_width=True):
            st.session_state.llm_client.update_api_url(api_url)
            if st.session_state.llm_client.test_connection():
                st.session_state.api_connected = True
                st.success("Connected")
            else:
                st.session_state.api_connected = False
                st.error("Failed")
        st.caption("🟢 Online" if st.session_state.api_connected else "🔴 Offline")
        
        st.divider()
        st.markdown("### Chats")
        if st.button("➕ New — Upload another video", use_container_width=True, type="primary"):
            new_chat()
            st.rerun()
        for c in st.session_state.chats:
            label = c["title"][:22] + "..." if len(c["title"]) > 22 else c["title"]
            if st.button(label, key=f"chat_{c['id']}", use_container_width=True):
                st.session_state.active_chat_id = c["id"]
                st.rerun()

def format_time(seconds):
    m, s = int(seconds // 60), int(seconds % 60)
    return f"{m:02d}:{s:02d}"

def render_chat_content(chat):
    lecture_id = chat.get("lecture_id")
    messages = chat.get("messages", [])
    
    if lecture_id is None:
        return render_upload(chat)
    
    db = SessionLocal()
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
    db.close()
    
    if not lecture:
        return render_upload(chat)
    
    if lecture.status == "processing":
        st.info("Processing in progress... Select another chat or wait.")
        return
    
    if lecture.status != "completed":
        st.warning("Processing failed. Start a new chat to upload again.")
        return
    
    for msg in messages:
        role = msg.get("role", "user")
        content = str(msg.get("content", ""))
        if role == "user":
            st.markdown(f"**You:** {content}")
        else:
            st.markdown(content)
    
    with st.form("chat_form", clear_on_submit=True):
        q = st.text_area("Ask anything about this lecture", placeholder="e.g. Explain the main concept...", height=80, label_visibility="collapsed")
        if st.form_submit_button("Send"):
            if q.strip() and st.session_state.api_connected:
                processor = LectureProcessor()
                db = SessionLocal()
                context = processor.get_lecture_context(lecture_id, db)
                result = st.session_state.llm_client.answer_question(q.strip(), context)
                db.close()
                if result["success"]:
                    chat["messages"].append({"role": "user", "content": q})
                    chat["messages"].append({"role": "assistant", "content": result["response"]})
                    save_chat_message(chat["id"], "user", q)
                    save_chat_message(chat["id"], "assistant", result["response"])
                    db = SessionLocal()
                    db.add(Query(lecture_id=lecture_id, query_text=q, response_text=result["response"]))
                    db.commit()
                    db.close()
                    st.rerun()
                else:
                    st.error(result.get("error", "Error"))

def render_upload(chat):
    st.markdown("**Upload a lecture video to get started**")
    st.caption("Supported: MP4, AVI, MOV, MKV, WEBM (max 500MB)")
    
    if not st.session_state.api_connected:
        st.warning("Connect to Colab API in the sidebar first.")
        return
    
    title = st.text_input("Lecture title", placeholder="e.g. Operating Systems - Week 3", label_visibility="collapsed")
    uploaded = st.file_uploader("Drop video here", type=["mp4", "avi", "mov", "mkv", "webm"], label_visibility="collapsed")
    
    if uploaded and title:
        size_mb = uploaded.size / (1024 * 1024)
        if size_mb > MAX_VIDEO_SIZE_MB:
            st.error(f"File too large (max {MAX_VIDEO_SIZE_MB}MB)")
        elif st.button("Process lecture", type="primary"):
            process_and_show(chat, uploaded, title)

def process_and_show(chat, uploaded_file, title):
    chat["title"] = "Processing..."
    update_chat_in_db(chat["id"], title="Processing...")
    video_path = UPLOAD_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}"
    with open(video_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    db = SessionLocal()
    lecture = Lecture(title=title, video_path=str(video_path), status="processing")
    db.add(lecture)
    db.commit()
    db.refresh(lecture)
    lid = lecture.id
    db.close()
    
    chat["lecture_id"] = lid
    update_chat_in_db(chat["id"], lecture_id=lid)

    progress = st.progress(0)
    status = st.empty()
    
    status.markdown("**Uploading...**")
    upload_result = st.session_state.llm_client.upload_video(str(video_path))
    if not upload_result["success"]:
        st.error(f"Upload failed: {upload_result.get('error')}")
        return
    
    job_id = upload_result["job_id"]
    while True:
        res = st.session_state.llm_client.get_job_status(job_id)
        if not res["success"]:
            break
        pct = res.get("progress", 0)
        status.markdown(f"**{res.get('message', '')}** — {pct}%")
        progress.progress(min(pct / 100, 1.0))
        if res["status"] == "completed":
            break
        if res["status"] == "failed":
            st.error(res.get("error", "Failed"))
            return
        time.sleep(2)
    
    result = st.session_state.llm_client.get_job_result(job_id)
    if not result["success"]:
        st.error(result.get("error"))
        return
    
    data = result["data"]
    transcript_data = data.get("transcript", [])
    frames_data = data.get("frames", [])
    duration = data.get("duration", 0)
    
    status.markdown("**Saving...**")
    db = SessionLocal()
    for seg in transcript_data:
        db.add(Transcript(lecture_id=lid, timestamp_start=seg["start"], timestamp_end=seg["end"], text=seg["text"], confidence=seg.get("confidence", 0)))
    db.commit()
    
    vp = VideoProcessor(str(video_path))
    vp.open_video()
    (PROCESSED_DIR / f"lecture_{lid}").mkdir(parents=True, exist_ok=True)
    vp.extract_audio(str(PROCESSED_DIR / f"lecture_{lid}" / "audio.wav"))
    extracted = vp.extract_frames(lid)
    vp.close()
    
    for i, (ts, fp) in enumerate(extracted):
        fd = frames_data[i] if i < len(frames_data) else {}
        db.add(Frame(lecture_id=lid, timestamp=ts, frame_path=fp, extracted_text=f"{fd.get('printed_text','')} {fd.get('handwritten_text','')}".strip(), printed_text=fd.get("printed_text",""), handwritten_text=fd.get("handwritten_text",""), ocr_confidence=fd.get("ocr_confidence",0)))
    db.commit()
    db.query(Lecture).filter(Lecture.id == lid).update({"status": "completed", "duration": duration, "processed_at": datetime.utcnow()})
    db.commit()
    
    processor = LectureProcessor()
    context = processor.get_lecture_context(lid, db)
    summary_result = st.session_state.llm_client.summarize_lecture(context)
    db.close()
    
    summary = summary_result.get("response", "Summary not available.") if summary_result.get("success") else "Could not generate summary."
    
    chat["messages"].append({"role": "assistant", "content": f"### Summary\n\n{summary}"})
    chat["title"] = title[:25] + "..." if len(title) > 25 else title
    save_chat_message(chat["id"], "assistant", f"### Summary\n\n{summary}")
    update_chat_in_db(chat["id"], lecture_id=lid, title=chat["title"])

    progress.progress(1.0)
    status.empty()
    st.success("Done! Scroll down to see full content and summary. Ask questions below.")
    st.balloons()
    st.rerun()

def render_full_content(lecture_id):
    db = SessionLocal()
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
    if not lecture:
        db.close()
        return
    
    transcripts = db.query(Transcript).filter(Transcript.lecture_id == lecture_id).order_by(Transcript.timestamp_start).all()
    frames = db.query(Frame).filter(Frame.lecture_id == lecture_id).order_by(Frame.timestamp).all()
    db.close()
    
    all_ev = []
    for t in transcripts:
        if t.text.strip():
            all_ev.append((t.timestamp_start, "speech", t.text))
    for f in frames:
        if f.printed_text and f.printed_text.strip():
            all_ev.append((f.timestamp, "slide", f.printed_text))
        if f.handwritten_text and f.handwritten_text.strip():
            all_ev.append((f.timestamp, "hand", f.handwritten_text))
    all_ev.sort(key=lambda x: x[0])
    
    with st.expander("📋 Full lecture content (speech + slides + handwriting)", expanded=False):
        for ts, typ, txt in all_ev:
            tstr = format_time(ts)
            cls = "event-speech" if typ == "speech" else "event-slide" if typ == "slide" else "event-hand"
            lbl = "🎤" if typ == "speech" else "🖼️" if typ == "slide" else "✍️"
            st.markdown(f'<div class="content-block {cls}"><b>{tstr} {lbl}</b> {html.escape(txt)}</div>', unsafe_allow_html=True)

def main():
    sidebar()
    
    st.markdown("# Lecture AI")
    
    cols = st.columns([1] * (len(st.session_state.chats) + 1))
    for i, c in enumerate(st.session_state.chats):
        with cols[i]:
            label = c["title"][:16] + ".." if len(c["title"]) > 16 else c["title"]
            if st.button(label, key=f"tab_{c['id']}", use_container_width=True):
                st.session_state.active_chat_id = c["id"]
                st.rerun()
    with cols[-1]:
        if st.button("➕ New video", key="tab_new", use_container_width=True, type="primary"):
            new_chat()
            st.rerun()
    
    st.caption("Upload a video → Get summary → Ask questions")
    
    chat = get_chat()
    
    if chat.get("lecture_id"):
        db = SessionLocal()
        lecture = db.query(Lecture).filter(Lecture.id == chat["lecture_id"]).first()
        db.close()
        
        if lecture and lecture.status == "completed":
            col_left, col_right = st.columns([2, 1])
            
            with col_left:
                render_full_content(chat["lecture_id"])
                render_chat_content(chat)
            
            with col_right:
                st.markdown("#### 🎬 Video")
                video_path = lecture.video_path
                if video_path and Path(video_path).exists():
                    ext = Path(video_path).suffix.lower()
                    fmt = "video/mp4" if ext in [".mp4", ".mov"] else "video/webm" if ext == ".webm" else "video/mp4"
                    st.video(video_path, format=fmt)
                else:
                    st.info("Video file not found")
            return
    
    render_chat_content(chat)

if __name__ == "__main__":
    main()
