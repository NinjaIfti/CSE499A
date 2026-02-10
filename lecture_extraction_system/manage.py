#!/usr/bin/env python
"""
Management utility for Lecture Extraction System
Provides commands for database management, cleanup, etc.
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session

from database import SessionLocal, Lecture, Transcript, Frame, Query, init_database
from config import UPLOAD_DIR, PROCESSED_DIR, DB_DIR

def list_lectures():
    """List all lectures in database"""
    db = SessionLocal()
    lectures = db.query(Lecture).order_by(Lecture.uploaded_at.desc()).all()
    
    if not lectures:
        print("No lectures found in database.")
        db.close()
        return
    
    print(f"\n{'ID':<5} {'Title':<30} {'Status':<12} {'Duration':<10} {'Uploaded':<20}")
    print("=" * 85)
    
    for lecture in lectures:
        duration = f"{lecture.duration:.1f}s" if lecture.duration else "N/A"
        uploaded = lecture.uploaded_at.strftime("%Y-%m-%d %H:%M")
        print(f"{lecture.id:<5} {lecture.title[:29]:<30} {lecture.status:<12} {duration:<10} {uploaded:<20}")
    
    print(f"\nTotal: {len(lectures)} lectures")
    db.close()

def lecture_info(lecture_id: int):
    """Show detailed info about a lecture"""
    db = SessionLocal()
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
    
    if not lecture:
        print(f"Lecture with ID {lecture_id} not found.")
        db.close()
        return
    
    transcript_count = db.query(Transcript).filter(Transcript.lecture_id == lecture_id).count()
    frame_count = db.query(Frame).filter(Frame.lecture_id == lecture_id).count()
    query_count = db.query(Query).filter(Query.lecture_id == lecture_id).count()
    
    print("\n" + "=" * 60)
    print(f"Lecture Information")
    print("=" * 60)
    print(f"ID:              {lecture.id}")
    print(f"Title:           {lecture.title}")
    print(f"Status:          {lecture.status}")
    print(f"Duration:        {lecture.duration:.1f}s" if lecture.duration else "Duration:        N/A")
    print(f"Video Path:      {lecture.video_path}")
    print(f"Uploaded:        {lecture.uploaded_at}")
    print(f"Processed:       {lecture.processed_at if lecture.processed_at else 'Not yet'}")
    print(f"\nTranscripts:     {transcript_count} segments")
    print(f"Frames:          {frame_count} frames")
    print(f"Queries:         {query_count} questions asked")
    print("=" * 60)
    
    db.close()

def delete_lecture(lecture_id: int, confirm: bool = False):
    """Delete a lecture and all associated data"""
    db = SessionLocal()
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
    
    if not lecture:
        print(f"Lecture with ID {lecture_id} not found.")
        db.close()
        return
    
    if not confirm:
        print(f"\nWARNING: This will delete lecture '{lecture.title}' and all associated data!")
        response = input("Are you sure? (yes/no): ")
        if response.lower() != 'yes':
            print("Deletion cancelled.")
            db.close()
            return
    
    # Delete associated files
    processed_dir = PROCESSED_DIR / f"lecture_{lecture_id}"
    if processed_dir.exists():
        import shutil
        shutil.rmtree(processed_dir)
        print(f"Deleted processed files: {processed_dir}")
    
    # Delete from database (cascades to transcripts, frames, queries)
    db.delete(lecture)
    db.commit()
    print(f"Deleted lecture: {lecture.title} (ID: {lecture_id})")
    
    db.close()

def cleanup_old():
    """Clean up old/failed lectures"""
    db = SessionLocal()
    
    # Find failed lectures
    failed = db.query(Lecture).filter(Lecture.status == 'failed').all()
    
    if not failed:
        print("No failed lectures to clean up.")
        db.close()
        return
    
    print(f"\nFound {len(failed)} failed lectures:")
    for lecture in failed:
        print(f"  - {lecture.title} (ID: {lecture.id})")
    
    response = input("\nDelete all failed lectures? (yes/no): ")
    if response.lower() == 'yes':
        for lecture in failed:
            delete_lecture(lecture.id, confirm=True)
        print(f"\nCleaned up {len(failed)} failed lectures.")
    else:
        print("Cleanup cancelled.")
    
    db.close()

def export_transcript(lecture_id: int, output_file: str = None):
    """Export lecture transcript to text file"""
    db = SessionLocal()
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
    
    if not lecture:
        print(f"Lecture with ID {lecture_id} not found.")
        db.close()
        return
    
    transcripts = db.query(Transcript).filter(
        Transcript.lecture_id == lecture_id
    ).order_by(Transcript.timestamp_start).all()
    
    if not transcripts:
        print(f"No transcript found for lecture ID {lecture_id}")
        db.close()
        return
    
    # Generate filename if not provided
    if not output_file:
        safe_title = "".join(c for c in lecture.title if c.isalnum() or c in (' ', '-', '_')).strip()
        output_file = f"{safe_title}_transcript.txt"
    
    # Write transcript
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Lecture: {lecture.title}\n")
        f.write(f"Duration: {lecture.duration:.1f}s\n")
        f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        for transcript in transcripts:
            mins = int(transcript.timestamp_start // 60)
            secs = int(transcript.timestamp_start % 60)
            f.write(f"[{mins:02d}:{secs:02d}] {transcript.text}\n")
    
    print(f"Transcript exported to: {output_file}")
    db.close()

def stats():
    """Show system statistics"""
    db = SessionLocal()
    
    total_lectures = db.query(Lecture).count()
    completed = db.query(Lecture).filter(Lecture.status == 'completed').count()
    processing = db.query(Lecture).filter(Lecture.status == 'processing').count()
    failed = db.query(Lecture).filter(Lecture.status == 'failed').count()
    
    total_transcripts = db.query(Transcript).count()
    total_frames = db.query(Frame).count()
    total_queries = db.query(Query).count()
    
    print("\n" + "=" * 50)
    print("System Statistics")
    print("=" * 50)
    print(f"\nLectures:")
    print(f"  Total:       {total_lectures}")
    print(f"  Completed:   {completed}")
    print(f"  Processing:  {processing}")
    print(f"  Failed:      {failed}")
    print(f"\nContent:")
    print(f"  Transcripts: {total_transcripts} segments")
    print(f"  Frames:      {total_frames} frames")
    print(f"  Queries:     {total_queries} questions")
    
    # Storage info
    upload_size = sum(f.stat().st_size for f in UPLOAD_DIR.rglob('*') if f.is_file()) / (1024**3)
    processed_size = sum(f.stat().st_size for f in PROCESSED_DIR.rglob('*') if f.is_file()) / (1024**3)
    
    print(f"\nStorage:")
    print(f"  Uploads:     {upload_size:.2f} GB")
    print(f"  Processed:   {processed_size:.2f} GB")
    print(f"  Total:       {upload_size + processed_size:.2f} GB")
    
    print("=" * 50)
    
    db.close()

def reset_database():
    """Reset the entire database (DANGEROUS!)"""
    print("\n⚠️  WARNING: This will DELETE ALL DATA!")
    print("This includes:")
    print("  - All lecture records")
    print("  - All transcripts")
    print("  - All frames")
    print("  - All queries")
    print("\nFiles in uploads/ and processed/ will NOT be deleted.")
    
    response = input("\nType 'DELETE ALL' to confirm: ")
    if response != 'DELETE ALL':
        print("Reset cancelled.")
        return
    
    # Drop and recreate tables
    from database import Base, engine
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    print("\n✅ Database has been reset.")

def main():
    parser = argparse.ArgumentParser(description='Lecture Extraction System Management')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List lectures
    subparsers.add_parser('list', help='List all lectures')
    
    # Lecture info
    info_parser = subparsers.add_parser('info', help='Show lecture details')
    info_parser.add_argument('lecture_id', type=int, help='Lecture ID')
    
    # Delete lecture
    delete_parser = subparsers.add_parser('delete', help='Delete a lecture')
    delete_parser.add_argument('lecture_id', type=int, help='Lecture ID')
    delete_parser.add_argument('-y', '--yes', action='store_true', help='Skip confirmation')
    
    # Cleanup
    subparsers.add_parser('cleanup', help='Clean up failed lectures')
    
    # Export transcript
    export_parser = subparsers.add_parser('export', help='Export transcript to file')
    export_parser.add_argument('lecture_id', type=int, help='Lecture ID')
    export_parser.add_argument('-o', '--output', help='Output file path')
    
    # Stats
    subparsers.add_parser('stats', help='Show system statistics')
    
    # Reset
    subparsers.add_parser('reset', help='Reset database (DANGEROUS!)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize database
    init_database()
    
    # Execute command
    if args.command == 'list':
        list_lectures()
    elif args.command == 'info':
        lecture_info(args.lecture_id)
    elif args.command == 'delete':
        delete_lecture(args.lecture_id, args.yes)
    elif args.command == 'cleanup':
        cleanup_old()
    elif args.command == 'export':
        export_transcript(args.lecture_id, args.output)
    elif args.command == 'stats':
        stats()
    elif args.command == 'reset':
        reset_database()

if __name__ == '__main__':
    main()
