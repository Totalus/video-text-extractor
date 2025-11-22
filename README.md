# Video Text Extractor

A Python tool that extracts images from video recordings and uses OCR (Optical Character Recognition) technology to extract texts from those images. The tool consists of two separate scripts that can be used independently or together:

1. **`extract_frames.py`** - Extracts frames from videos with intelligent filtering
2. **`extract_text.py`** - Performs OCR on extracted frames to detect text

This modular approach allows you to extract frames once and experiment with different OCR settings, or to process frames from other sources.

## Disclamer

I value transparency in the use of AI tool and find my responsability to indicate when AI tool was significantly used in my projects.

This tool was entirely vibe coded using Claude Sonnet 4.5.

## Features

### Frame extraction
- **Frame Extraction**: Extract frames from video at configurable intervals
- **Deduplication**: Ignore identical frames
- **Transition detection**: Ignore images that are part of a transition/animation
- **Blur Detection**: Optionally filter out blurry frames

### Text extraction
- **Text Grouping**: Intelligently group and sort text blocks to identify paragraphs properly
- **Text Metadata**: Text are extracted from the images with metadata (position, size, confidence score)

## Requirements

### System Requirements
- Python 3.7+
- Tesseract OCR (must be installed separately)

### Installing Tesseract OCR

Tesseract must be installed separately.

**Linux:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
Download the installer from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)

### Python dependencies

Create a virtualenv and install dependencies automatically:

```bash
./setup.sh
```

Or install them manually:

```bash
pip install -r requirements.txt
```
