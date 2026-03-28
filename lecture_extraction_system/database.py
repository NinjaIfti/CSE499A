from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from config import DATABASE_URL

Base = declarative_base()
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


class Lecture(Base):
    __tablename__ = "lectures"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    video_path = Column(String(500), nullable=False)
    duration = Column(Float)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    status = Column(String(50), default="uploaded")
    rag_job_id = Column(String(100), nullable=True)

    transcripts = relationship("Transcript", back_populates="lecture", cascade="all, delete-orphan")
    frames = relationship("Frame", back_populates="lecture", cascade="all, delete-orphan")
    queries = relationship("Query", back_populates="lecture", cascade="all, delete-orphan")


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id"))
    timestamp_start = Column(Float)
    timestamp_end = Column(Float)
    text = Column(Text)
    confidence = Column(Float)

    lecture = relationship("Lecture", back_populates="transcripts")


class Frame(Base):
    __tablename__ = "frames"

    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id"))
    timestamp = Column(Float)
    frame_path = Column(String(500))
    extracted_text = Column(Text)
    handwritten_text = Column(Text)
    printed_text = Column(Text)
    ocr_confidence = Column(Float)

    lecture = relationship("Lecture", back_populates="frames")


class Query(Base):
    __tablename__ = "queries"

    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id"))
    query_text = Column(Text)
    response_text = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    lecture = relationship("Lecture", back_populates="queries")


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id"), nullable=True)
    title = Column(String(255), default="New chat")
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Stored per assistant message so clips/timestamps survive page reloads
    clip_id = Column(String(100), nullable=True)
    timestamp_label = Column(String(50), nullable=True)
    timestamp_start = Column(Float, nullable=True)
    timestamp_end = Column(Float, nullable=True)


def _safe_add_column(conn, ddl: str):
    try:
        conn.execute(text(ddl))
        conn.commit()
    except Exception:
        pass


def init_database():
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        # lectures table additions
        _safe_add_column(conn, "ALTER TABLE lectures ADD COLUMN rag_job_id VARCHAR(100)")

        # chat_messages table additions
        _safe_add_column(conn, "ALTER TABLE chat_messages ADD COLUMN clip_id VARCHAR(100)")
        _safe_add_column(conn, "ALTER TABLE chat_messages ADD COLUMN timestamp_label VARCHAR(50)")
        _safe_add_column(conn, "ALTER TABLE chat_messages ADD COLUMN timestamp_start FLOAT")
        _safe_add_column(conn, "ALTER TABLE chat_messages ADD COLUMN timestamp_end FLOAT")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
