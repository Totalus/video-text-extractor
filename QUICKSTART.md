# Quick Start Guide

## Installation

1. **Clone or download this repository**

2. **Install Tesseract OCR** (system requirement):
   ```bash
   # Linux
   sudo apt-get update && sudo apt-get install tesseract-ocr
   
   # macOS
   brew install tesseract
   
   # Windows - download from:
   # https://github.com/UB-Mannheim/tesseract/wiki
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify installation**:
   ```bash
   python check_dependencies.py
   ```

## Quick Usage Examples

### Example 1: Basic Usage
Extract text from a video with default settings (500ms intervals, blur filtering, deduplication enabled):
```bash
python video_text_extractor.py my_video.mp4
```

**Output:**
- Images saved to: `images/` directory
- JSON results: `output.json`

---

### Example 2: High-Quality Screen Recording
For presentations or screen recordings with crisp text:
```bash
python video_text_extractor.py presentation.mp4 \
  --interval 1000 \
  --blur-threshold 80 \
  --output presentation_text.json \
  --images-dir presentation_frames
```

**Why these settings:**
- `--interval 1000`: Captures 1 frame per second (screen recordings don't change as frequently)
- `--blur-threshold 80`: Stricter blur filtering for clear text
- Custom output paths for organization

---

### Example 3: Fast Processing
Process a long video quickly by extracting fewer frames:
```bash
python video_text_extractor.py long_video.mp4 \
  --interval 2000 \
  --output quick_results.json
```

**Why these settings:**
- `--interval 2000`: Only 1 frame every 2 seconds
- Default filtering reduces redundant processing

---

### Example 4: Maximum Frame Capture
Keep all frames without any filtering (testing/debugging):
```bash
python video_text_extractor.py video.mp4 \
  --no-deduplicate \
  --no-filter-blurry \
  --interval 250
```

**Why these settings:**
- `--no-deduplicate`: Keep duplicate frames
- `--no-filter-blurry`: Keep blurry frames
- `--interval 250`: Capture 4 frames per second

---

### Example 5: Multi-line Text Preserved
For documents or slides with multiple lines of text:
```bash
python video_text_extractor.py lecture.mp4 \
  --join-char newline \
  --output lecture_notes.json
```

**Why these settings:**
- `--join-char newline`: Preserves line breaks in text
- Useful for extracting structured content like lists or paragraphs

---

## Understanding the Output

### JSON Structure
```json
[
  {
    "file": "images/0000000.png",
    "timestamp_ms": 0,
    "text": [
      {
        "value": "Welcome to the presentation",
        "x": 150,
        "y": 100,
        "width": 450,
        "height": 35,
        "confidence": 94.2
      }
    ]
  }
]
```

### What Each Field Means:
- **file**: Path to the extracted image frame
- **timestamp_ms**: Time in video when frame was captured (in milliseconds)
- **text**: Array of detected text blocks
  - **value**: The actual text content
  - **x, y**: Position of text (top-left corner)
  - **width, height**: Size of text bounding box
  - **confidence**: OCR confidence (0-100, higher is better)

---

## Typical Workflows

### Workflow 1: Extract Text from Tutorial Video
```bash
# 1. Run extraction
python video_text_extractor.py tutorial.mp4 --interval 2000 --output tutorial.json

# 2. Review images/ directory to see extracted frames
# 3. Open tutorial.json to see extracted text with timestamps
```

### Workflow 2: Extract Subtitles from Video
```bash
# Extract frames every 500ms to catch all subtitle changes
python video_text_extractor.py movie.mp4 \
  --interval 500 \
  --blur-threshold 120 \
  --output subtitles.json

# Process the JSON to extract only bottom-of-screen text (typical subtitle position)
```

### Workflow 3: Quality Testing
```bash
# 1. Test with different thresholds to find optimal setting
python video_text_extractor.py sample.mp4 --blur-threshold 50 --images-dir test_50
python video_text_extractor.py sample.mp4 --blur-threshold 100 --images-dir test_100
python video_text_extractor.py sample.mp4 --blur-threshold 150 --images-dir test_150

# 2. Review the test_* directories to see which threshold works best
# 3. Use the optimal threshold for full processing
```

---

## Troubleshooting Common Issues

### Issue: "Tesseract is not installed"
**Solution:** Install Tesseract OCR system package (see Installation section)

### Issue: No text detected in output
**Possible causes:**
1. Text too small or blurry in video
2. Blur threshold too strict - try increasing it
3. Check extracted images to verify text is visible

**Try:**
```bash
python video_text_extractor.py video.mp4 --blur-threshold 150
```

### Issue: Too many similar frames
**Solution:** Deduplication should be enabled by default, but verify:
```bash
python video_text_extractor.py video.mp4 --deduplicate
```

### Issue: Processing is very slow
**Solutions:**
1. Increase interval between frames:
   ```bash
   python video_text_extractor.py video.mp4 --interval 2000
   ```
2. Enable all filtering (should be default):
   ```bash
   python video_text_extractor.py video.mp4 --deduplicate --filter-blurry
   ```

### Issue: Missing frames with important text
**Solution:** Decrease interval or lower blur threshold:
```bash
python video_text_extractor.py video.mp4 --interval 250 --blur-threshold 150
```

---

## Performance Tips

### For Fast Processing:
- Use longer intervals (1000-2000ms)
- Enable blur filtering and deduplication (default)
- Process smaller video segments for testing

### For Maximum Accuracy:
- Use shorter intervals (250-500ms)
- Lower blur threshold (50-80) for screen recordings
- Review extracted images to verify quality

### For Large Videos:
- Start with high interval (2000ms+) to test
- Adjust based on content change frequency
- Consider processing in segments

---

## Next Steps

1. ✓ Install dependencies
2. ✓ Test with a sample video
3. ✓ Adjust parameters based on results
4. ✓ Process your full video
5. ✓ Extract insights from the JSON output

For more details, see the main [README.md](README.md).
