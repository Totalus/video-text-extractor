# Video Text Extractor

A Python script that extracts text from video recordings using OCR (Optical Character Recognition) technology.

## Features

- **Frame Extraction**: Extract frames from video at configurable intervals
- **Blur Detection**: Automatically filter out blurry frames using Laplacian variance
- **Deduplication**: Skip duplicate frames using perceptual hashing
- **OCR Processing**: Extract text from images with confidence scores
- **Text Grouping**: Intelligently group and sort text blocks
- **Progress Tracking**: Real-time progress bars and detailed statistics
- **JSON Output**: Structured output with text positions and confidence scores

## Requirements

### System Requirements
- Python 3.7+
- Tesseract OCR (must be installed separately)

### Installing Tesseract OCR

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

### Python Dependencies

Install Python packages:
```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install opencv-python>=4.8.0 pytesseract>=0.3.10 Pillow>=10.0.0 imagehash>=4.3.1 tqdm>=4.65.0 numpy>=1.24.0
```

## Usage

### Basic Usage

```bash
python video_text_extractor.py <video_file>
```

Example:
```bash
python video_text_extractor.py presentation.mp4
```

### Command-Line Options

```
positional arguments:
  video_file            Path to input video file

optional arguments:
  -h, --help            Show help message and exit
  --interval INTERVAL   Time interval in milliseconds between frame captures (default: 500)
  --deduplicate         Enable frame deduplication (default)
  --no-deduplicate      Disable frame deduplication
  --filter-blurry       Enable blurry frame filtering (default)
  --no-filter-blurry    Disable blurry frame filtering
  --blur-threshold THRESHOLD
                        Laplacian variance threshold for blur detection (default: 100.0)
  --join-char {space,newline}
                        Character to join multi-line text (default: space)
  --output OUTPUT       Path for output JSON file (default: output.json)
  --images-dir DIR      Directory to save extracted images (default: images)
```

### Examples

**Extract frames every second:**
```bash
python video_text_extractor.py presentation.mp4 --interval 1000
```

**Custom output file and directory:**
```bash
python video_text_extractor.py presentation.mp4 --interval 1000 --output results.json --images-dir frames
```

**Adjust blur threshold for screen recordings:**
```bash
python video_text_extractor.py screencast.mp4 --blur-threshold 80
```

**Join multi-line text with newlines:**
```bash
python video_text_extractor.py presentation.mp4 --join-char newline
```

**Disable all filtering (keep all frames):**
```bash
python video_text_extractor.py video.mp4 --no-deduplicate --no-filter-blurry
```

**Complete example with all options:**
```bash
python video_text_extractor.py presentation.mp4 \
  --interval 1000 \
  --deduplicate \
  --filter-blurry \
  --blur-threshold 100 \
  --join-char newline \
  --output results.json \
  --images-dir frames
```

## Blur Threshold Guidelines

The blur threshold determines how strict the blur filtering is. Adjust based on your video type:

- **50-80**: Strict filtering - Good for screen recordings and presentations
- **100-150**: Moderate filtering - Good for general videos (default: 100)
- **150-200**: Lenient filtering - Only filters severe blur
- **Higher values**: More permissive, fewer frames filtered

**Tips:**
- Test with sample frames first
- Screen recordings typically need lower thresholds (50-80)
- Camera footage may need higher thresholds (100-150)
- Adjust based on video quality and content type

## Output Format

The script generates a JSON file with the following structure:

```json
[
  {
    "file": "images/0000000.png",
    "timestamp_ms": 0,
    "text": [
      {
        "value": "extracted text here",
        "x": 100,
        "y": 50,
        "width": 200,
        "height": 30,
        "confidence": 85.5
      },
      {
        "value": "more text",
        "x": 100,
        "y": 90,
        "width": 180,
        "height": 28,
        "confidence": 92.3
      }
    ]
  },
  {
    "file": "images/0000500.png",
    "timestamp_ms": 500,
    "text": []
  }
]
```

**Fields:**
- `file`: Path to the extracted image
- `timestamp_ms`: Timestamp in milliseconds from video start
- `text`: Array of detected text blocks (empty if no text found)
  - `value`: The extracted text content
  - `x`, `y`: Top-left coordinates of text bounding box
  - `width`, `height`: Dimensions of text bounding box
  - `confidence`: OCR confidence score (0-100)

## How It Works

### 1. Frame Extraction
- Opens video file and extracts frames at specified intervals
- Starting from 0ms, captures frames every `interval_ms` milliseconds

### 2. Blur Detection (Optional)
- Uses Laplacian variance to detect blurry frames
- Calculates edge sharpness in grayscale image
- Skips frames below the threshold
- Filters out transition effects and motion blur

### 3. Deduplication (Optional)
- Uses perceptual hashing (pHash) to compare frames
- Compares current frame with last saved frame
- Only saves frames that are sufficiently different (hash difference > 5)
- Reduces redundant frames from static content

### 4. Text Extraction
- Performs OCR using Tesseract on each saved image
- Filters out low-confidence results (< 30%)
- Groups text blocks that are vertically close (within 10px)
- Groups blocks with similar heights (within 20% difference)
- Sorts text top-to-bottom, then left-to-right

### 5. Output Generation
- Compiles results into structured JSON format
- Includes position coordinates and confidence scores
- Saves all data to specified output file

## Statistics

During execution, the script displays:

**Frame Extraction:**
```
Extracting frames: 45/120 (37%) | Saved: 18 | Blurry: 8 | Duplicates: 19
```

**Text Extraction:**
```
Extracting text: 38/45 (84%)
```

**Final Summary:**
```
=== Extraction Complete ===
Total time: 2m 34s
Frames extracted: 120
Frames skipped (blurry): 23
Frames skipped (duplicates): 52
Total images saved: 45
Text detections: 128
Output saved to: output.json
```

## Performance Considerations

- **Processing time** depends on video length, resolution, and interval
- **Blur detection** adds minimal overhead (~5-10ms per frame)
- **Deduplication** adds ~10-20ms per frame comparison
- **OCR** is the slowest step (~100-500ms per image)

### Optimization Tips

1. **Use larger intervals** for long videos (e.g., 1000ms or more)
2. **Enable filtering** to reduce OCR workload (both blur and deduplication)
3. **Lower resolution** videos process faster but may reduce OCR accuracy
4. **Adjust blur threshold** to balance quality and processing time

## Error Handling

The script handles various error conditions:

- **Video file not found**: Clear error message with file path
- **Cannot open video**: Error for unsupported formats or codecs
- **OCR failures**: Warnings logged, processing continues
- **No frames extracted**: Error if video processing yields no frames
- **Tesseract not installed**: Installation instructions provided
- **Invalid arguments**: Help message displayed

## Troubleshooting

**"Tesseract is not installed" error:**
- Install Tesseract OCR for your operating system (see Requirements section)
- Ensure Tesseract is in your system PATH

**No text detected:**
- Verify image quality (frames not too blurry)
- Try adjusting blur threshold
- Check if text is clearly visible in extracted images
- Ensure text language is supported by Tesseract

**Too many frames being filtered:**
- Increase blur threshold (e.g., 150 or 200)
- Disable filtering temporarily to check frame quality
- Adjust interval to capture fewer frames

**Processing too slow:**
- Increase frame interval (--interval 1000 or higher)
- Enable blur filtering and deduplication
- Process smaller section of video for testing

## License

This project is open source and available for use and modification.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.
