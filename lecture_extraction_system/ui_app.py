import datetime
import html
import re
import time
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional
import shutil

import streamlit as st

from config import (
    UPLOAD_DIR,
    VIDEO_FORMATS,
    MAX_VIDEO_SIZE_MB,
    COLAB_API_URL,
    PROCESSED_DIR,
)
from database import (
    init_database,
    SessionLocal,
    Lecture,
    Transcript,
    Frame,
    Query,
    Chat,
    ChatMessage,
)
from lecture_processor import LectureProcessor
from llm_client import LLMClient


init_database()

_HTML_TAG_RE = re.compile(r"<[^>]+>")

def clean_llm_response(text: str) -> str:
    """Strip any stray HTML tags the model may have included in its output."""
    return _HTML_TAG_RE.sub("", text).strip()


@contextmanager
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_llm_client() -> LLMClient:
    if "llm_client" not in st.session_state:
        st.session_state.llm_client = LLMClient()
    return st.session_state.llm_client


# ─────────────────────────────────────────────────────────────────────────────
# Page config & styles
# ─────────────────────────────────────────────────────────────────────────────

def set_page_config():
    st.set_page_config(
        page_title="LectureMind AI",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="collapsed",
    )


def inject_styles():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap');

    html, body, [class*="css"], .stMarkdown, .stText { font-family: 'Inter', sans-serif !important; }

    [data-testid="stSidebar"] { display: none !important; }
    header[data-testid="stHeader"] { display: none !important; }
    #MainMenu { display: none !important; }
    footer { display: none !important; }

    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 3rem !important;
        max-width: 1180px !important;
    }

    /* ── Top bar ─────────────────────────────────── */
    .topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.85rem 1.6rem;
        background: linear-gradient(135deg, #1e1b4b 0%, #3730a3 55%, #4f46e5 100%);
        border-radius: 1rem;
        margin-bottom: 0.4rem;
        box-shadow: 0 6px 28px rgba(79,70,229,0.28);
    }
    .topbar-brand { display: flex; align-items: center; gap: 0.85rem; }
    .topbar-icon {
        font-size: 1.45rem;
        background: rgba(255,255,255,0.14);
        width: 46px; height: 46px;
        border-radius: 0.8rem;
        display: flex; align-items: center; justify-content: center;
        backdrop-filter: blur(6px);
        border: 1px solid rgba(255,255,255,0.18);
    }
    .topbar-name {
        font-size: 1.2rem; font-weight: 700;
        color: #ffffff; letter-spacing: -0.02em;
    }
    .topbar-tagline {
        font-size: 0.71rem; color: rgba(255,255,255,0.52);
        margin-top: 1px;
    }
    .conn-pill {
        display: inline-flex; align-items: center; gap: 0.45rem;
        padding: 0.32rem 0.9rem;
        border-radius: 999px;
        font-size: 0.74rem; font-weight: 500;
        border: 1px solid rgba(255,255,255,0.22);
        color: rgba(255,255,255,0.88);
    }
    .dot-ok  { width:7px;height:7px;border-radius:50%;background:#22c55e;box-shadow:0 0 0 3px rgba(34,197,94,.3); }
    .dot-err { width:7px;height:7px;border-radius:50%;background:#f87171; }

    /* ── Section headings ────────────────────────── */
    .pg-title { font-size: 1.25rem; font-weight: 700; color: #0f172a; margin-bottom: 0.15rem; }
    .pg-sub   { font-size: 0.82rem; color: #64748b; margin-bottom: 1.2rem; line-height: 1.5; }

    /* ── Generic card ────────────────────────────── */
    .card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 1rem;
        padding: 1.35rem 1.5rem;
        box-shadow: 0 1px 6px rgba(0,0,0,0.04);
        margin-bottom: 1rem;
    }

    /* ── Upload pipeline steps ───────────────────── */
    .step { display:flex; align-items:flex-start; gap:0.75rem; padding:0.55rem 0; border-bottom:1px solid #f1f5f9; }
    .step:last-child { border-bottom:none; }
    .step-num {
        min-width:26px; height:26px; border-radius:50%;
        background: linear-gradient(135deg,#4f46e5,#7c3aed);
        color:#fff; font-size:0.7rem; font-weight:700;
        display:flex; align-items:center; justify-content:center; flex-shrink:0; margin-top:2px;
    }
    .step-body { font-size:0.82rem; color:#374151; line-height:1.5; }
    .step-body strong { color:#111827; }

    /* ── Lecture status pills ────────────────────── */
    .lec-pill { display:inline-block; padding:2px 10px; border-radius:999px; font-size:0.72rem; font-weight:600; }
    .lec-completed { background:#d1fae5; color:#065f46; border:1px solid #6ee7b7; }
    .lec-processing { background:#fef3c7; color:#92400e; border:1px solid #fcd34d; }
    .lec-failed     { background:#fee2e2; color:#991b1b; border:1px solid #fca5a5; }
    .lec-uploaded   { background:#dbeafe; color:#1e40af; border:1px solid #93c5fd; }

    /* ── Metric boxes ────────────────────────────── */
    .mbox { background:#f8fafc; border:1px solid #e2e8f0; border-radius:0.8rem; padding:0.9rem 1rem; text-align:center; }
    .mbox-lbl { font-size:0.69rem; text-transform:uppercase; letter-spacing:.07em; color:#64748b; }
    .mbox-val { font-size:1.2rem; font-weight:700; color:#0f172a; margin-top:0.2rem; }

    /* ── Chat bubbles ────────────────────────────── */
    .msg-user-row   { display:flex; justify-content:flex-end;  gap:0.5rem; margin-bottom:1rem; }
    .msg-assist-row { display:flex; justify-content:flex-start; gap:0.5rem; margin-bottom:0.5rem; }

    .avatar {
        width:32px; height:32px; border-radius:50%;
        display:flex; align-items:center; justify-content:center;
        font-size:0.85rem; flex-shrink:0; margin-top:3px;
    }
    .av-ai   { background:linear-gradient(135deg,#4f46e5,#7c3aed); color:#fff; }
    .av-user { background:#e2e8f0; color:#374151; }

    .bub-user {
        background: linear-gradient(135deg,#4f46e5,#6366f1);
        color: #fff;
        padding: 0.65rem 1.05rem;
        border-radius: 18px 18px 4px 18px;
        max-width: 70%;
        font-size: 0.875rem; line-height: 1.62;
        box-shadow: 0 3px 12px rgba(79,70,229,0.22);
        white-space: pre-wrap;
        word-wrap: break-word;
        overflow-wrap: break-word;
    }
    .bub-assist {
        background: #ffffff;
        color: #0f172a;
        padding: 0.72rem 1.08rem;
        border-radius: 4px 18px 18px 18px;
        max-width: 78%;
        font-size: 0.875rem; line-height: 1.68;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 10px rgba(0,0,0,0.06);
        white-space: pre-wrap;
        word-wrap: break-word;
        overflow-wrap: break-word;
    }
    .msg-time { font-size:0.68rem; color:#94a3b8; margin-top:4px; }
    .msg-time-r { text-align:right; }

    .ts-pill {
        display:inline-flex; align-items:center; gap:0.35rem;
        background:#fff7ed; border:1px solid #fed7aa; color:#c2410c;
        font-size:0.72rem; font-weight:600;
        padding:3px 10px; border-radius:999px; margin-top:0.45rem;
    }

    .empty-state { text-align:center; padding:3rem 1rem; color:#94a3b8; }
    .empty-icon  { font-size:2.6rem; margin-bottom:0.6rem; }
    .empty-text  { font-size:0.85rem; line-height:1.6; }

    /* ── Tab strip ───────────────────────────────── */
    [data-baseweb="tab-list"] {
        gap:0.2rem !important;
        background:#f1f5f9 !important;
        padding:0.25rem !important;
        border-radius:0.75rem !important;
        border:none !important;
        margin-bottom:1.1rem !important;
    }
    [data-baseweb="tab"] {
        border-radius:0.6rem !important;
        padding:0.42rem 1.2rem !important;
        font-size:0.84rem !important;
        font-weight:500 !important;
        color:#64748b !important;
        border:none !important;
        background:transparent !important;
        transition: all .15s ease;
    }
    [aria-selected="true"][data-baseweb="tab"] {
        background:#ffffff !important;
        color:#4f46e5 !important;
        box-shadow:0 1px 5px rgba(0,0,0,0.1) !important;
        font-weight:600 !important;
    }
    [data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display:none !important; }

    /* ── Misc button tweaks ──────────────────────── */
    .stButton > button { border-radius:0.6rem !important; font-weight:500 !important; font-size:0.84rem !important; }
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Connection modal
# ─────────────────────────────────────────────────────────────────────────────

@st.dialog("Connect to AI backend", width="medium")
def connection_modal():
    if "api_url" not in st.session_state:
        st.session_state.api_url = COLAB_API_URL

    st.markdown("**Backend URL**")
    st.caption("Paste the ngrok URL from your Colab session. The server must expose `/health`, `/upload`, and `/generate`.")

    api_url = st.text_input(
        "Server URL",
        value=st.session_state.api_url,
        placeholder="https://xxxx.ngrok-free.app",
        label_visibility="collapsed",
    )
    st.session_state.api_url = api_url
    client = get_llm_client()
    client.update_api_url(api_url)

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Test connection", type="primary", use_container_width=True):
            with st.spinner("Checking..."):
                ok = client.test_connection()
            st.session_state.backend_ok = ok
            if ok:
                st.success("Connected! Closing...")
                time.sleep(0.8)
                st.rerun()
    with col2:
        backend_ok = st.session_state.get("backend_ok", None)
        if backend_ok is True:
            st.success("Connected ✅")
        elif backend_ok is False:
            st.error("Unreachable ⚠️")


# ─────────────────────────────────────────────────────────────────────────────
# Top navigation bar
# ─────────────────────────────────────────────────────────────────────────────

def render_top_nav():
    backend_ok = st.session_state.get("backend_ok", None)

    if backend_ok is True:
        dot_html = '<span class="dot-ok"></span>'
        label = "AI Backend Connected"
    else:
        dot_html = '<span class="dot-err"></span>'
        label = "Backend Disconnected"

    st.markdown(f"""
    <div class="topbar">
        <div class="topbar-brand">
            <div class="topbar-icon">🎓</div>
            <div>
                <div class="topbar-name">LectureMind AI</div>
                <div class="topbar-tagline">Lecture Extraction &amp; Intelligent Q&amp;A</div>
            </div>
        </div>
        <span class="conn-pill">{dot_html} {label}</span>
    </div>
    """, unsafe_allow_html=True)

    _, btn_col = st.columns([7, 1])
    with btn_col:
        if st.button("⚙️ Backend", use_container_width=True, key="nav_backend_btn"):
            connection_modal()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def save_uploaded_video(uploaded_file) -> Path:
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = uploaded_file.name.replace(" ", "_")
    dest = UPLOAD_DIR / f"{timestamp}_{safe_name}"
    with open(dest, "wb") as f:
        f.write(uploaded_file.read())
    return dest


def human_duration(seconds: float) -> str:
    if not seconds or seconds <= 0:
        return "N/A"
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}m {secs:02d}s" if mins else f"{secs}s"


def status_pill(status: str) -> str:
    cls_map = {
        "completed": "lec-completed",
        "processing": "lec-processing",
        "failed": "lec-failed",
        "uploaded": "lec-uploaded",
    }
    cls = cls_map.get(status.lower(), "lec-uploaded")
    return f'<span class="lec-pill {cls}">{status.title()}</span>'


def load_lectures() -> List[Lecture]:
    with db_session() as db:
        return db.query(Lecture).order_by(Lecture.uploaded_at.desc()).all()


def remove_lecture(lecture_id: int, video_path: str, rag_job_id: Optional[str]) -> Optional[str]:
    with db_session() as db:
        lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
        if not lecture:
            return "Lecture not found"
        chats = db.query(Chat).filter(Chat.lecture_id == lecture_id).all()
        for chat in chats:
            db.query(ChatMessage).filter(ChatMessage.chat_id == chat.id).delete()
        db.query(Chat).filter(Chat.lecture_id == lecture_id).delete()
        db.delete(lecture)
        db.commit()

    if rag_job_id:
        get_llm_client().delete_job(rag_job_id)

    lecture_job_ids = st.session_state.get("lecture_job_ids", {})
    lecture_job_ids.pop(lecture_id, None)
    st.session_state.lecture_job_ids = lecture_job_ids

    if video_path and Path(video_path).exists():
        try:
            Path(video_path).unlink()
        except Exception:
            pass

    processed_dir = PROCESSED_DIR / f"lecture_{lecture_id}"
    if processed_dir.exists():
        try:
            shutil.rmtree(processed_dir)
        except Exception:
            pass

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Chat rendering
# ─────────────────────────────────────────────────────────────────────────────

def render_chat_messages(messages: list, client: LLMClient):
    """Render message history with styled bubbles. For assistant messages that have
    a stored clip_id, embed the video player directly below the bubble."""

    if not messages:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">💬</div>
            <div class="empty-text">
                No messages yet.<br>Ask a question below to start the conversation.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    backend_ok = st.session_state.get("backend_ok", False)

    for msg in messages:
        time_str = msg.created_at.strftime("%H:%M")
        escaped = html.escape(msg.content or "")

        if msg.role == "user":
            st.markdown(f"""
            <div class="msg-user-row">
                <div>
                    <div class="bub-user">{escaped}</div>
                    <div class="msg-time msg-time-r">{time_str}</div>
                </div>
                <div class="avatar av-user">👤</div>
            </div>
            """, unsafe_allow_html=True)

        else:
            ts_html = ""
            if msg.timestamp_label:
                ts_html = f'<div><span class="ts-pill">📍 {html.escape(msg.timestamp_label)}</span></div>'

            st.markdown(f"""
            <div class="msg-assist-row">
                <div class="avatar av-ai">🤖</div>
                <div>
                    <div class="bub-assist">{escaped}</div>
                    {ts_html}
                    <div class="msg-time">{time_str}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Embed clip when available — stored clip_id persists across page loads
            if msg.clip_id and backend_ok:
                clip_url = client.get_clip_url(msg.clip_id)
                _, video_col, _ = st.columns([1, 10, 1])
                with video_col:
                    st.caption(f"📹 Relevant lecture clip · {msg.timestamp_label or ''}")
                    st.video(clip_url)
            elif msg.clip_id and not backend_ok:
                _, note_col = st.columns([1, 10])
                with note_col:
                    st.caption(f"📍 Clip available at {msg.timestamp_label} — connect to backend to play.")


# ─────────────────────────────────────────────────────────────────────────────
# Upload & Process page
# ─────────────────────────────────────────────────────────────────────────────

def upload_and_process_page():
    # Handle pending local processing after RAG upload
    if st.session_state.get("after_rag_lecture_id"):
        lid = st.session_state.after_rag_lecture_id
        dpath = st.session_state.after_rag_dest_path
        with db_session() as db:
            lec = db.query(Lecture).filter(Lecture.id == lid).first()
            video_path = lec.video_path if lec else ""
            rag_job_id = (lec.rag_job_id if lec else None) or st.session_state.get("lecture_job_ids", {}).get(lid)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**Lecture saved.** Choose what to do next:")
        c1, c2 = st.columns(2)
        with c1:
            start_local = st.button("▶ Run local processing", type="primary", use_container_width=True)
        with c2:
            cancel = st.button("✕ Remove lecture", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        if cancel:
            remove_lecture(lid, video_path, rag_job_id)
            del st.session_state.after_rag_lecture_id
            del st.session_state.after_rag_dest_path
            st.success("Lecture removed.")
            st.rerun()
        if start_local:
            del st.session_state.after_rag_lecture_id
            del st.session_state.after_rag_dest_path
            st.session_state.run_processor_lecture_id = lid
            st.session_state.run_processor_dest_path = dpath
            st.rerun()

    if st.session_state.get("run_processor_lecture_id"):
        lid = st.session_state.run_processor_lecture_id
        dpath = st.session_state.run_processor_dest_path
        del st.session_state.run_processor_lecture_id
        del st.session_state.run_processor_dest_path

        progress_bar = st.progress(0)
        status_ph = st.empty()

        def progress_callback(message: str, value: int):
            status_ph.write(message)
            progress_bar.progress(max(0, min(100, value)))

        processor = LectureProcessor()
        with db_session() as db:
            ok = processor.process_lecture(lid, dpath, db, progress_callback)

        if ok:
            progress_bar.progress(100)
            status_ph.write("Complete.")
            st.success("Lecture processed successfully.")
        else:
            st.error("Processing failed. Check the logs.")
        return

    # ── Main upload UI ──
    st.markdown('<div class="pg-title">Upload Lecture</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="pg-sub">Upload a recorded lecture video. The system will transcribe the audio, '
        'extract text from slides, and build a searchable knowledge base.</div>',
        unsafe_allow_html=True,
    )

    allowed_exts = [ext.lstrip(".") for ext in VIDEO_FORMATS]

    left, right = st.columns([1.6, 1.2], gap="large")

    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        uploaded = st.file_uploader(
            "Drop a video file here",
            type=allowed_exts,
            help=f"Supported: {', '.join(allowed_exts)}",
        )
        st.caption(f"Maximum file size: {MAX_VIDEO_SIZE_MB} MB")
        start = st.button(
            "🚀 Start processing",
            type="primary",
            use_container_width=True,
            disabled=uploaded is None,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**Processing pipeline**")
        steps = [
            ("1", "<strong>Audio extraction</strong> — FFmpeg pulls the audio track"),
            ("2", "<strong>Transcription</strong> — Whisper converts speech to text with timestamps"),
            ("3", "<strong>Frame OCR</strong> — PaddleOCR reads slide and board text"),
            ("4", "<strong>RAG indexing</strong> — LangChain + ChromaDB builds the retrieval store"),
        ]
        for num, text in steps:
            st.markdown(
                f'<div class="step"><div class="step-num">{num}</div>'
                f'<div class="step-body">{text}</div></div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    if not (start and uploaded is not None):
        return

    size_mb = uploaded.size / (1024 * 1024)
    if size_mb > MAX_VIDEO_SIZE_MB:
        st.error(f"File is {size_mb:.1f} MB — limit is {MAX_VIDEO_SIZE_MB} MB.")
        return

    ext = Path(uploaded.name).suffix.lower()
    if ext not in VIDEO_FORMATS:
        st.error("Unsupported video format.")
        return

    with st.spinner("Saving video…"):
        dest_path = save_uploaded_video(uploaded)

    with db_session() as db:
        lecture = Lecture(
            title=Path(uploaded.name).stem,
            video_path=str(dest_path),
            status="uploaded",
        )
        db.add(lecture)
        db.commit()
        db.refresh(lecture)
        lecture_id = lecture.id

    client = get_llm_client()
    with st.spinner("Uploading to AI backend for RAG indexing…"):
        upload_result = client.upload_video(str(dest_path))

    if not upload_result.get("success"):
        st.session_state.backend_ok = False
        st.warning(f"RAG backend upload failed: {upload_result.get('error', 'unknown error')}")
        st.info(f"Lecture #{lecture_id} saved locally. You can still run local processing.")
        st.session_state.after_rag_lecture_id = lecture_id
        st.session_state.after_rag_dest_path = str(dest_path)
        st.rerun()
        return

    job_id = upload_result.get("job_id")
    status_ph = st.empty()
    progress_bar = st.progress(0)

    while True:
        status_result = client.get_job_status(job_id)
        if not status_result.get("success"):
            st.session_state.backend_ok = False
            st.warning("Lost connection while checking RAG status.")
            break

        status = status_result.get("status", "")
        progress = status_result.get("progress", 0)
        message = status_result.get("message", "")
        status_ph.write(f"⏳ {message}")
        progress_bar.progress(max(0, min(100, progress)))

        if status == "completed":
            lecture_job_ids = st.session_state.get("lecture_job_ids", {})
            lecture_job_ids[lecture_id] = job_id
            st.session_state.lecture_job_ids = lecture_job_ids
            st.session_state.job_id = job_id
            with db_session() as db:
                lec = db.query(Lecture).filter(Lecture.id == lecture_id).first()
                if lec:
                    lec.rag_job_id = job_id
                    db.commit()
            progress_bar.progress(100)
            status_ph.write("✅ RAG indexing complete.")
            st.success("Lecture is ready for Q&A!")
            break

        if status == "failed":
            st.warning(f"RAG indexing failed: {status_result.get('error', 'unknown error')}")
            break

        time.sleep(2)

    st.session_state.after_rag_lecture_id = lecture_id
    st.session_state.after_rag_dest_path = str(dest_path)
    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Past Lectures page
# ─────────────────────────────────────────────────────────────────────────────

def past_lectures_page():
    st.markdown('<div class="pg-title">Past Lectures</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="pg-sub">Browse your processed lectures, inspect their metadata, and manage RAG indexing.</div>',
        unsafe_allow_html=True,
    )

    lectures = load_lectures()
    if not lectures:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">📚</div>
            <div class="empty-text">No lectures yet — upload one in the Upload tab.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    options = [f"#{lec.id} — {lec.title}" for lec in lectures]
    idx = st.selectbox(
        "Select lecture",
        options=list(range(len(lectures))),
        format_func=lambda i: options[i],
    )
    selected = lectures[idx]
    st.session_state.selected_lecture_id = selected.id

    # Info card
    st.markdown('<div class="card">', unsafe_allow_html=True)

    header_l, header_r = st.columns([3, 1])
    with header_l:
        st.markdown(f"### {selected.title}")
    with header_r:
        st.markdown(
            f'<div style="text-align:right;margin-top:0.5rem;">{status_pill(selected.status)}</div>',
            unsafe_allow_html=True,
        )

    m1, m2, m3, m4 = st.columns(4)
    cells = [
        (m1, "Duration", human_duration(selected.duration)),
        (m2, "Uploaded", selected.uploaded_at.strftime("%b %d, %Y")),
        (m3, "Time", selected.uploaded_at.strftime("%H:%M")),
        (m4, "File", Path(selected.video_path).name),
    ]
    for col, label, value in cells:
        with col:
            st.markdown(
                f'<div class="mbox"><div class="mbox-lbl">{label}</div>'
                f'<div class="mbox-val" style="font-size:0.9rem;">{value}</div></div>',
                unsafe_allow_html=True,
            )

    st.write("")

    with db_session() as db:
        t_count = db.query(Transcript).filter(Transcript.lecture_id == selected.id).count()
        f_count = db.query(Frame).filter(Frame.lecture_id == selected.id).count()
        q_count = db.query(Query).filter(Query.lecture_id == selected.id).count()

    job_id = selected.rag_job_id or st.session_state.get("lecture_job_ids", {}).get(selected.id)

    s1, s2, s3, s4 = st.columns(4)
    stats = [
        (s1, "Transcript segments", str(t_count)),
        (s2, "Frames (OCR)", str(f_count)),
        (s3, "Questions asked", str(q_count)),
        (s4, "RAG job", job_id[:8] + "…" if job_id else "Not indexed"),
    ]
    for col, label, value in stats:
        with col:
            st.markdown(
                f'<div class="mbox"><div class="mbox-lbl">{label}</div>'
                f'<div class="mbox-val">{value}</div></div>',
                unsafe_allow_html=True,
            )

    st.write("")
    act1, act2, _ = st.columns([1, 1, 3])

    with act1:
        if not job_id and st.button("☁ Register for RAG", use_container_width=True):
            video_path = Path(selected.video_path)
            if not video_path.exists():
                st.error("Video file not found on disk.")
            else:
                client = get_llm_client()
                with st.spinner("Uploading to AI backend…"):
                    upload_result = client.upload_video(str(video_path))
                if not upload_result.get("success"):
                    st.session_state.backend_ok = False
                    st.error(upload_result.get("error", "Upload failed."))
                else:
                    new_job_id = upload_result.get("job_id")
                    sts = st.empty()
                    prg = st.progress(0)
                    while True:
                        sr = client.get_job_status(new_job_id)
                        if not sr.get("success"):
                            st.warning("Lost connection.")
                            break
                        prg.progress(max(0, min(100, sr.get("progress", 0))))
                        sts.write(sr.get("message", ""))
                        if sr.get("status") == "completed":
                            with db_session() as db:
                                lec = db.query(Lecture).filter(Lecture.id == selected.id).first()
                                if lec:
                                    lec.rag_job_id = new_job_id
                                    db.commit()
                            ids = st.session_state.get("lecture_job_ids", {})
                            ids[selected.id] = new_job_id
                            st.session_state.lecture_job_ids = ids
                            prg.progress(100)
                            sts.write("Done.")
                            st.success(f"RAG indexed. Job: {new_job_id[:8]}…")
                            st.rerun()
                        if sr.get("status") == "failed":
                            st.warning(f"Indexing failed: {sr.get('error', '')}")
                            break
                        time.sleep(2)

    with act2:
        if st.button("🗑 Remove lecture", use_container_width=True):
            err = remove_lecture(selected.id, selected.video_path, selected.rag_job_id)
            if err:
                st.error(err)
            else:
                st.success("Lecture and all data removed.")
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Q&A page
# ─────────────────────────────────────────────────────────────────────────────

def qa_page():
    st.markdown('<div class="pg-title">Interactive Q&amp;A</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="pg-sub">Ask questions about any processed lecture. '
        'The AI retrieves the most relevant segments and shows you exactly where in the video the answer is.</div>',
        unsafe_allow_html=True,
    )

    lectures = load_lectures()
    if not lectures:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">🎬</div>
            <div class="empty-text">No lectures available.<br>Upload and process a lecture first.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    default_id = st.session_state.get("selected_lecture_id", lectures[0].id)
    default_index = next((i for i, lec in enumerate(lectures) if lec.id == default_id), 0)

    options = [f"#{lec.id} — {lec.title} ({lec.status})" for lec in lectures]
    idx = st.selectbox(
        "Lecture",
        options=list(range(len(lectures))),
        index=default_index,
        format_func=lambda i: options[i],
    )
    selected = lectures[idx]
    st.session_state.selected_lecture_id = selected.id

    client = get_llm_client()

    with db_session() as db:
        processor = LectureProcessor()
        context = processor.get_lecture_context(selected.id, db)

        chat = (
            db.query(Chat)
            .filter(Chat.lecture_id == selected.id)
            .order_by(Chat.created_at.asc())
            .first()
        )
        if not chat:
            chat = Chat(lecture_id=selected.id, title=f"Lecture #{selected.id} chat")
            db.add(chat)
            db.commit()
            db.refresh(chat)

        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.chat_id == chat.id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )

    if context:
        st.caption(f"📄 Local context: {len(context):,} characters · {len(messages) // 2} exchange(s) saved")

    # ── Chat history ──
    render_chat_messages(messages, client)

    # ── Input area ──
    st.markdown('<div class="card">', unsafe_allow_html=True)
    question = st.text_area(
        "Your question",
        placeholder="e.g. What is the definition of a convolutional layer? How does backpropagation work?",
        height=100,
        label_visibility="collapsed",
    )
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        max_tokens = st.slider("Max tokens", 100, 1000, 500, step=50)
    with c2:
        temperature = st.slider("Temperature", 0.0, 1.5, 0.7, step=0.1)
    with c3:
        ask = st.button("💬 Ask question", type="primary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if not (ask and question.strip()):
        return

    with st.spinner("Thinking…"):
        job_id = selected.rag_job_id or st.session_state.get("lecture_job_ids", {}).get(selected.id)
        result = client.generate_response(
            prompt=question.strip(),
            context=context,
            max_tokens=max_tokens,
            temperature=temperature,
            job_id=job_id,
        )

    if not result["success"]:
        st.session_state.backend_ok = False
        st.error(result.get("error") or "Backend returned an error.")
        return

    answer = clean_llm_response(result["response"])
    clip_id = result.get("clip_id")
    timestamp = result.get("timestamp")
    ts_label = timestamp.get("label") if timestamp else None
    ts_start = timestamp.get("start") if timestamp else None
    ts_end = timestamp.get("end") if timestamp else None

    # Persist to database — include clip and timestamp data on the assistant message
    with db_session() as db:
        chat = (
            db.query(Chat)
            .filter(Chat.lecture_id == selected.id)
            .order_by(Chat.created_at.asc())
            .first()
        )
        if not chat:
            chat = Chat(lecture_id=selected.id, title=f"Lecture #{selected.id} chat")
            db.add(chat)
            db.commit()
            db.refresh(chat)

        user_msg = ChatMessage(chat_id=chat.id, role="user", content=question.strip())
        asst_msg = ChatMessage(
            chat_id=chat.id,
            role="assistant",
            content=answer,
            clip_id=clip_id,
            timestamp_label=ts_label,
            timestamp_start=ts_start,
            timestamp_end=ts_end,
        )
        q = Query(
            lecture_id=selected.id,
            query_text=question.strip(),
            response_text=answer,
        )
        db.add_all([user_msg, asst_msg, q])
        db.commit()

    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    set_page_config()
    inject_styles()

    if "api_url" not in st.session_state:
        st.session_state.api_url = COLAB_API_URL
    client = get_llm_client()
    client.update_api_url(st.session_state.api_url)

    if st.session_state.get("backend_ok") is not True:
        connection_modal()

    render_top_nav()

    tab_upload, tab_past, tab_qa = st.tabs(
        ["📤 Upload & Process", "📚 Past Lectures", "💬 Q&A"]
    )

    with tab_upload:
        upload_and_process_page()

    with tab_past:
        past_lectures_page()

    with tab_qa:
        qa_page()


if __name__ == "__main__":
    main()
