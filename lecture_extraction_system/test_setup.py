#!/usr/bin/env python
"""
Test script to verify installation and setup
Run this after installation to check if everything is working
"""

import sys
from pathlib import Path

def test_imports():
    """Test if all required packages are installed"""
    print("🧪 Testing package imports...")
    
    required_packages = [
        ('streamlit', 'Streamlit'),
        ('whisper', 'OpenAI Whisper'),
        ('cv2', 'OpenCV'),
        ('easyocr', 'EasyOCR'),
        ('torch', 'PyTorch'),
        ('transformers', 'Transformers'),
        ('sqlalchemy', 'SQLAlchemy'),
        ('PIL', 'Pillow'),
        ('numpy', 'NumPy'),
        ('pandas', 'Pandas'),
    ]
    
    failed = []
    
    for package, name in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {name}")
        except ImportError as e:
            print(f"  ❌ {name} - {str(e)}")
            failed.append(name)
    
    if failed:
        print(f"\n❌ Failed to import: {', '.join(failed)}")
        print("Please run: pip install -r requirements.txt")
        return False
    else:
        print("\n✅ All packages imported successfully!")
        return True

def test_directories():
    """Test if required directories exist"""
    print("\n🧪 Testing directory structure...")
    
    required_dirs = ['uploads', 'processed', 'database']
    
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"  ✅ {dir_name}/")
        else:
            dir_path.mkdir(exist_ok=True)
            print(f"  ✨ Created {dir_name}/")
    
    print("\n✅ Directory structure OK!")
    return True

def test_ffmpeg():
    """Test if FFmpeg is installed"""
    print("\n🧪 Testing FFmpeg...")
    
    import subprocess
    
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )
        if result.returncode == 0:
            version_line = result.stdout.decode().split('\n')[0]
            print(f"  ✅ {version_line}")
            return True
        else:
            print("  ❌ FFmpeg found but returned error")
            return False
    except FileNotFoundError:
        print("  ❌ FFmpeg not found!")
        print("  Install FFmpeg:")
        print("    Windows: choco install ffmpeg")
        print("    Linux: sudo apt install ffmpeg")
        print("    Mac: brew install ffmpeg")
        return False
    except Exception as e:
        print(f"  ❌ Error testing FFmpeg: {e}")
        return False

def test_gpu():
    """Test GPU availability"""
    print("\n🧪 Testing GPU availability...")
    
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            print(f"  ✅ GPU available: {gpu_name}")
            print(f"  ℹ️ CUDA version: {torch.version.cuda}")
            return True
        else:
            print("  ⚠️ No GPU detected (CPU mode)")
            print("  ℹ️ Processing will be slower but will work")
            return True
    except Exception as e:
        print(f"  ⚠️ Could not test GPU: {e}")
        return True

def test_database():
    """Test database setup"""
    print("\n🧪 Testing database setup...")
    
    try:
        from database import init_database, SessionLocal, Lecture
        
        # Initialize database
        init_database()
        print("  ✅ Database initialized")
        
        # Test connection
        db = SessionLocal()
        count = db.query(Lecture).count()
        db.close()
        print(f"  ✅ Database connection OK ({count} lectures)")
        
        return True
    except Exception as e:
        print(f"  ❌ Database error: {e}")
        return False

def test_local_imports():
    """Test local module imports"""
    print("\n🧪 Testing local modules...")
    
    modules = [
        'config',
        'database',
        'llm_client',
        'video_processor',
        'audio_processor',
        'ocr_processor',
        'lecture_processor',
    ]
    
    failed = []
    
    for module in modules:
        try:
            __import__(module)
            print(f"  ✅ {module}.py")
        except Exception as e:
            print(f"  ❌ {module}.py - {str(e)}")
            failed.append(module)
    
    if failed:
        print(f"\n❌ Failed to import: {', '.join(failed)}")
        return False
    else:
        print("\n✅ All local modules loaded!")
        return True

def main():
    """Run all tests"""
    print("=" * 50)
    print("🔍 Lecture Extraction System - Setup Test")
    print("=" * 50)
    print()
    
    results = []
    
    results.append(("Package Imports", test_imports()))
    results.append(("Directory Structure", test_directories()))
    results.append(("FFmpeg", test_ffmpeg()))
    results.append(("GPU Detection", test_gpu()))
    results.append(("Local Modules", test_local_imports()))
    results.append(("Database", test_database()))
    
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! You're ready to use the system!")
        print("\nTo start the application:")
        print("  Windows: run.bat")
        print("  Linux/Mac: streamlit run app.py")
    else:
        print("\n⚠️ Some tests failed. Please fix the issues above.")
        print("Refer to INSTALLATION.md for troubleshooting.")
        sys.exit(1)

if __name__ == "__main__":
    main()
