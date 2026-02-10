import streamlit as st
import os
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session
import time

from database import init_database, SessionLocal, Lecture, Transcript, Frame, Query
from lecture_processor import LectureProcessor
from llm_client import LLMClient
from config import UPLOAD_DIR, VIDEO_FORMATS, MAX_VIDEO_SIZE_MB

st.set_page_config(
    page_title="Lecture AI - Smart Learning Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional look
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(120deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        color: #64748b;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .stat-value {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .stat-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        border-left: 4px solid #667eea;
        background: #f8fafc;
    }
    .chat-question {
        font-weight: 600;
        color: #1e293b;
        margin-bottom: 0.5rem;
    }
    .chat-answer {
        color: #475569;
        line-height: 1.6;
    }
    .upload-box {
        border: 2px dashed #cbd5e1;
        border-radius: 1rem;
        padding: 2rem;
        text-align: center;
        background: #f8fafc;
        transition: all 0.3s;
    }
    .upload-box:hover {
        border-color: #667eea;
        background: #f1f5f9;
    }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.875rem;
        font-weight: 500;
    }
    .status-completed { background: #dcfce7; color: #166534; }
    .status-processing { background: #fef3c7; color: #92400e; }
    .status-failed { background: #fee2e2; color: #991b1b; }
    .transcript-item {
        padding: 0.75rem;
        border-left: 3px solid #e2e8f0;
        margin-bottom: 0.5rem;
        background: white;
        border-radius: 0.5rem;
    }
    .timestamp {
        color: #667eea;
        font-weight: 600;
        font-size: 0.875rem;
    }
    .stButton>button {
        border-radius: 0.5rem;
        font-weight: 500;
        transition: all 0.3s;
    }
    .connection-success {
        background: #dcfce7;
        color: #166534;
        padding: 0.75rem;
        border-radius: 0.5rem;
        font-weight: 500;
    }
    .connection-error {
        background: #fee2e2;
        color: #991b1b;
        padding: 0.75rem;
        border-radius: 0.5rem;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

init_database()

if 'llm_client' not in st.session_state:
    st.session_state.llm_client = LLMClient()
if 'current_lecture_id' not in st.session_state:
    st.session_state.current_lecture_id = None
if 'api_connected' not in st.session_state:
    st.session_state.api_connected = False
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

def sidebar():
    with st.sidebar:
        st.markdown("### ⚙️ API Configuration")
        
        api_url = st.text_input(
            "Colab API URL",
            value=st.session_state.llm_client.api_url,
            placeholder="https://xxxx.ngrok.io",
            help="Paste your Google Colab ngrok URL here"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔌 Connect", use_container_width=True):
                st.session_state.llm_client.update_api_url(api_url)
                with st.spinner("Testing..."):
                    if st.session_state.llm_client.test_connection():
                        st.session_state.api_connected = True
                        st.success("Connected!")
                    else:
                        st.session_state.api_connected = False
                        st.error("Failed")
        
        with col2:
            if st.session_state.api_connected:
                st.markdown('<div class="connection-success">🟢 Online</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="connection-error">🔴 Offline</div>', unsafe_allow_html=True)
        
        st.divider()
        
        st.markdown("### 📚 Your Lectures")
        
        db = SessionLocal()
        lectures = db.query(Lecture).order_by(Lecture.uploaded_at.desc()).all()
        db.close()
        
        if lectures:
            for lecture in lectures:
                status_class = f"status-{lecture.status}"
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if st.button(f"📹 {lecture.title[:20]}...", key=f"lec_{lecture.id}", use_container_width=True):
                            st.session_state.current_lecture_id = lecture.id
                            st.rerun()
                    with col2:
                        st.markdown(f'<span class="status-badge {status_class}">{lecture.status[:4]}</span>', unsafe_allow_html=True)
        else:
            st.info("No lectures yet")
        
        st.divider()
        st.caption("Made with ❤️ for learning")

def main():
    sidebar()
    
    st.markdown('<h1 class="main-header">🎓 Lecture AI</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Upload lectures, extract content, and chat with an AI tutor</p>', unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload", "💬 Chat", "📝 Content", "📊 Stats"])
    
    with tab1:
        upload_tab()
    
    with tab2:
        chat_tab()
    
    with tab3:
        content_tab()
    
    with tab4:
        stats_tab()

def upload_tab():
    st.markdown("### Upload New Lecture")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        with st.container():
            lecture_title = st.text_input(
                "Lecture Title",
                placeholder="e.g., Machine Learning - Week 1",
                help="Give your lecture a descriptive name"
            )
            
            uploaded_file = st.file_uploader(
                "Choose Video File",
                type=['mp4', 'avi', 'mov', 'mkv', 'webm'],
                help=f"Max size: {MAX_VIDEO_SIZE_MB}MB"
            )
            
            if uploaded_file and lecture_title:
                file_size_mb = uploaded_file.size / (1024 * 1024)
                
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("File Size", f"{file_size_mb:.1f} MB")
                with col_b:
                    st.metric("Format", uploaded_file.name.split('.')[-1].upper())
                with col_c:
                    status = "✅ Ready" if file_size_mb <= MAX_VIDEO_SIZE_MB else "❌ Too Large"
                    st.metric("Status", status)
                
                if file_size_mb <= MAX_VIDEO_SIZE_MB:
                    if st.button("🚀 Process Lecture", type="primary", use_container_width=True):
                        process_video(uploaded_file, lecture_title)
                else:
                    st.error(f"File too large. Maximum size is {MAX_VIDEO_SIZE_MB}MB")
    
    with col2:
        st.markdown("#### Processing Pipeline")
        st.markdown("""
        <div style="background: #f8fafc; padding: 1rem; border-radius: 0.5rem;">
        
        **1. Video Upload** 📹  
        Upload your lecture video
        
        **2. Audio Extraction** 🎵  
        Separate audio track
        
        **3. Transcription** 📝  
        Speech-to-text with Whisper
        
        **4. Frame Analysis** 🖼️  
        Extract key frames
        
        **5. OCR Processing** 🔍  
        Read text from slides
        
        **6. AI Ready** 🤖  
        Ask questions!
        
        </div>
        """, unsafe_allow_html=True)

def process_video(uploaded_file, title):
    video_path = UPLOAD_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}"
    with open(video_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    db = SessionLocal()
    lecture = Lecture(title=title, video_path=str(video_path), status="uploaded")
    db.add(lecture)
    db.commit()
    db.refresh(lecture)
    lecture_id = lecture.id
    db.close()
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def update_progress(message, percent):
        status_text.markdown(f"**{message}**")
        progress_bar.progress(percent)
    
    processor = LectureProcessor()
    db = SessionLocal()
    
    success = processor.process_lecture(lecture_id, str(video_path), db, progress_callback=update_progress)
    
    db.close()
    
    if success:
        st.success("✅ Lecture processed successfully!")
        st.session_state.current_lecture_id = lecture_id
        st.balloons()
        time.sleep(2)
        st.rerun()
    else:
        st.error("❌ Processing failed")

def chat_tab():
    st.markdown("### 💬 Chat with Your Lecture")
    
    if not st.session_state.current_lecture_id:
        st.warning("Select a lecture from the sidebar first")
        return
    
    if not st.session_state.api_connected:
        st.warning("Connect to the LLM API in the sidebar")
        return
    
    db = SessionLocal()
    lecture = db.query(Lecture).filter(Lecture.id == st.session_state.current_lecture_id).first()
    
    if not lecture or lecture.status != "completed":
        st.warning("Lecture is still processing. Please wait.")
        db.close()
        return
    
    st.markdown(f"**📖 {lecture.title}**")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        query_mode = st.selectbox(
            "Mode",
            ["💭 Ask Question", "📚 Explain Topic", "📄 Summarize"],
            label_visibility="collapsed"
        )
    
    user_input = st.text_area(
        "Your question",
        placeholder="What would you like to know?",
        height=100,
        label_visibility="collapsed"
    )
    
    col_a, col_b = st.columns([1, 4])
    with col_a:
        if st.button("🚀 Ask", type="primary", use_container_width=True):
            if user_input or "Summarize" in query_mode:
                with st.spinner("Thinking..."):
                    processor = LectureProcessor()
                    context = processor.get_lecture_context(st.session_state.current_lecture_id, db)
                    
                    llm_client = st.session_state.llm_client
                    
                    if "Summarize" in query_mode:
                        result = llm_client.summarize_lecture(context)
                    elif "Explain" in query_mode:
                        result = llm_client.explain_topic(user_input, context)
                    else:
                        result = llm_client.answer_question(user_input, context)
                    
                    if result["success"]:
                        st.session_state.chat_history.insert(0, {
                            "question": user_input if user_input else "Summarize this lecture",
                            "answer": result["response"],
                            "time": datetime.now().strftime("%H:%M")
                        })
                        
                        query = Query(
                            lecture_id=st.session_state.current_lecture_id,
                            query_text=user_input if user_input else "Summarize",
                            response_text=result["response"]
                        )
                        db.add(query)
                        db.commit()
                        st.rerun()
                    else:
                        st.error(f"Error: {result.get('error')}")
    
    st.divider()
    
    if st.session_state.chat_history:
        st.markdown("### Recent Conversations")
        for item in st.session_state.chat_history[:10]:
            st.markdown(f"""
            <div class="chat-message">
                <div class="chat-question">Q: {item['question']}</div>
                <div class="chat-answer">{item['answer']}</div>
                <small style="color: #94a3b8;">🕐 {item['time']}</small>
            </div>
            """, unsafe_allow_html=True)
    
    db.close()

def content_tab():
    st.markdown("### 📝 Lecture Content")
    
    if not st.session_state.current_lecture_id:
        st.warning("Select a lecture from the sidebar")
        return
    
    db = SessionLocal()
    lecture = db.query(Lecture).filter(Lecture.id == st.session_state.current_lecture_id).first()
    
    if not lecture:
        st.warning("Lecture not found")
        db.close()
        return
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        status_class = f"status-{lecture.status}"
        st.markdown(f'<div class="stat-card"><div class="stat-value">{lecture.status.upper()}</div><div class="stat-label">Status</div></div>', unsafe_allow_html=True)
    with col2:
        duration = f"{lecture.duration:.0f}s" if lecture.duration else "N/A"
        st.markdown(f'<div class="stat-card"><div class="stat-value">{duration}</div><div class="stat-label">Duration</div></div>', unsafe_allow_html=True)
    with col3:
        transcript_count = db.query(Transcript).filter(Transcript.lecture_id == lecture.id).count()
        st.markdown(f'<div class="stat-card"><div class="stat-value">{transcript_count}</div><div class="stat-label">Segments</div></div>', unsafe_allow_html=True)
    with col4:
        frame_count = db.query(Frame).filter(Frame.lecture_id == lecture.id).count()
        st.markdown(f'<div class="stat-card"><div class="stat-value">{frame_count}</div><div class="stat-label">Frames</div></div>', unsafe_allow_html=True)
    
    if lecture.status != "completed":
        st.info("Content will be available after processing")
        db.close()
        return
    
    st.divider()
    
    tab_a, tab_b, tab_c = st.tabs(["🎤 Transcript", "🖼️ Slides (Printed)", "✍️ Handwriting"])
    
    with tab_a:
        transcripts = db.query(Transcript).filter(
            Transcript.lecture_id == lecture.id
        ).order_by(Transcript.timestamp_start).all()
        
        st.markdown(f"**{len(transcripts)} segments**")
        
        for transcript in transcripts:
            time_str = format_time(transcript.timestamp_start)
            st.markdown(f"""
            <div class="transcript-item">
                <span class="timestamp">{time_str}</span>
                <p style="margin: 0.5rem 0 0 0; color: #1e293b;">{transcript.text}</p>
            </div>
            """, unsafe_allow_html=True)
    
    with tab_b:
        frames = db.query(Frame).filter(
            Frame.lecture_id == lecture.id,
            Frame.printed_text != ""
        ).order_by(Frame.timestamp).all()
        
        st.markdown(f"**{len(frames)} frames with printed text**")
        
        for frame in frames:
            if frame.printed_text and frame.printed_text.strip():
                time_str = format_time(frame.timestamp)
                with st.expander(f"⏱️ {time_str} - {frame.ocr_confidence:.0%} confidence"):
                    st.write(frame.printed_text)
    
    with tab_c:
        frames = db.query(Frame).filter(
            Frame.lecture_id == lecture.id,
            Frame.handwritten_text != ""
        ).order_by(Frame.timestamp).all()
        
        st.markdown(f"**{len(frames)} frames with handwriting**")
        
        for frame in frames:
            if frame.handwritten_text and frame.handwritten_text.strip():
                time_str = format_time(frame.timestamp)
                with st.expander(f"⏱️ {time_str} - {frame.ocr_confidence:.0%} confidence"):
                    st.write(frame.handwritten_text)
    
    db.close()

def stats_tab():
    st.markdown("### 📊 System Statistics")
    
    db = SessionLocal()
    
    total_lectures = db.query(Lecture).count()
    completed = db.query(Lecture).filter(Lecture.status == 'completed').count()
    processing = db.query(Lecture).filter(Lecture.status == 'processing').count()
    failed = db.query(Lecture).filter(Lecture.status == 'failed').count()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="stat-card"><div class="stat-value">{total_lectures}</div><div class="stat-label">Total Lectures</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-card"><div class="stat-value">{completed}</div><div class="stat-label">Completed</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="stat-card"><div class="stat-value">{processing}</div><div class="stat-label">Processing</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="stat-card"><div class="stat-value">{failed}</div><div class="stat-label">Failed</div></div>', unsafe_allow_html=True)
    
    st.divider()
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.markdown("#### Recent Lectures")
        lectures = db.query(Lecture).order_by(Lecture.uploaded_at.desc()).limit(5).all()
        for lecture in lectures:
            status_class = f"status-{lecture.status}"
            st.markdown(f"""
            <div style="padding: 1rem; background: white; border-radius: 0.5rem; margin-bottom: 0.5rem; border-left: 4px solid #667eea;">
                <strong>{lecture.title}</strong>
                <br>
                <span class="status-badge {status_class}">{lecture.status}</span>
                <small style="color: #94a3b8; margin-left: 0.5rem;">{lecture.uploaded_at.strftime('%Y-%m-%d %H:%M')}</small>
            </div>
            """, unsafe_allow_html=True)
    
    with col_b:
        st.markdown("#### Storage Usage")
        
        upload_size = sum(f.stat().st_size for f in UPLOAD_DIR.rglob('*') if f.is_file()) / (1024**3) if UPLOAD_DIR.exists() else 0
        
        st.metric("Videos", f"{upload_size:.2f} GB")
        
        total_queries = db.query(Query).count()
        st.metric("Questions Asked", total_queries)
        
        total_transcripts = db.query(Transcript).count()
        st.metric("Transcript Segments", total_transcripts)
    
    db.close()

def format_time(seconds):
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

if __name__ == "__main__":
    main()
