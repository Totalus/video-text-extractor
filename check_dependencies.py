#!/usr/bin/env python3
"""
Quick test script to verify that all dependencies are installed correctly.
Run this before using the video_text_extractor to check your environment.
"""

import sys

def check_dependencies():
    """Check if all required dependencies are installed."""
    print("Checking dependencies...\n")
    
    missing_deps = []
    installed_deps = []
    
    # Check Python version
    print(f"Python version: {sys.version.split()[0]}", end=" ")
    if sys.version_info >= (3, 7):
        print("✓")
    else:
        print("✗ (Python 3.7+ required)")
        missing_deps.append("Python 3.7+")
    
    # Check OpenCV
    try:
        import cv2
        print(f"opencv-python: {cv2.__version__} ✓")
        installed_deps.append("opencv-python")
    except ImportError:
        print("opencv-python: Not installed ✗")
        missing_deps.append("opencv-python")
    
    # Check NumPy
    try:
        import numpy as np
        print(f"numpy: {np.__version__} ✓")
        installed_deps.append("numpy")
    except ImportError:
        print("numpy: Not installed ✗")
        missing_deps.append("numpy")
    
    # Check Pillow
    try:
        from PIL import Image
        import PIL
        print(f"Pillow: {PIL.__version__} ✓")
        installed_deps.append("Pillow")
    except ImportError:
        print("Pillow: Not installed ✗")
        missing_deps.append("Pillow")
    
    # Check pytesseract
    try:
        import pytesseract
        print(f"pytesseract: Installed ✓")
        installed_deps.append("pytesseract")
        
        # Check if Tesseract binary is available
        try:
            version = pytesseract.get_tesseract_version()
            print(f"  Tesseract OCR: {version} ✓")
        except pytesseract.TesseractNotFoundError:
            print("  Tesseract OCR: Not found ✗")
            print("  Please install Tesseract:")
            print("    Linux:   sudo apt-get install tesseract-ocr")
            print("    macOS:   brew install tesseract")
            print("    Windows: https://github.com/UB-Mannheim/tesseract/wiki")
            missing_deps.append("tesseract-ocr (system package)")
    except ImportError:
        print("pytesseract: Not installed ✗")
        missing_deps.append("pytesseract")
    
    # Check imagehash
    try:
        import imagehash
        print(f"imagehash: Installed ✓")
        installed_deps.append("imagehash")
    except ImportError:
        print("imagehash: Not installed ✗")
        missing_deps.append("imagehash")
    
    # Check tqdm
    try:
        import tqdm
        print(f"tqdm: {tqdm.__version__} ✓")
        installed_deps.append("tqdm")
    except ImportError:
        print("tqdm: Not installed ✗")
        missing_deps.append("tqdm")
    
    # Summary
    print("\n" + "=" * 50)
    if missing_deps:
        print(f"✗ Missing {len(missing_deps)} dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\nTo install Python packages, run:")
        print("  pip install -r requirements.txt")
        print("\nOr install individually:")
        print("  pip install opencv-python pytesseract Pillow imagehash tqdm numpy")
        return False
    else:
        print(f"✓ All dependencies installed! ({len(installed_deps)} packages)")
        print("\nYou're ready to use the video_text_extractor!")
        return True

if __name__ == "__main__":
    success = check_dependencies()
    sys.exit(0 if success else 1)
