# Video Text Extractor

A Python script that extracts images from video recordings and uses OCR (Optical Character Recognition) technology to extract texts from those images. The output produces a folder with the extracted images and a file that contains the texts detected for each image.

## Disclamer

I value transparency in the use of AI tool and find my responsability to indicate when AI tool was significantly used in my projects.

This tool was entirely vibe coded using Claude Sonnet 4.5.

## Features

- **Frame Extraction**: Extract frames from video at configurable intervals
- **Blur Detection**: Optionally filter out blurry frames
- **Deduplication**: Ignore identical frames
- **Transition detection**: Optionally ignore images that are part of a transition/animation
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


## Usage

### As a Command-Line Tool

**Basic Usage:**

```bash
python video_text_extractor.py <video_file>
```

### As a Python Library

```python
from video_text_lib import extract_frames, extract_text_from_image

# Extract frames from video
saved_frames, stats = extract_frames(
    video_path="presentation.mp4",
    interval_ms=1000,
    deduplicate=True,
    filter_blurry=True,
    blur_threshold=100.0,
    images_dir="images"
)

# Extract text from an image
text_blocks = extract_text_from_image("images/0001000.png", join_char='space')

# See example_library_usage.py for more examples
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
  --filter-blurry       Enable blurry frame filtering
  --no-filter-blurry    Disable blurry frame filtering (default)
  --blur-threshold THRESHOLD
                        Laplacian variance threshold for blur detection (default: 100.0)
  --check-stability     Enable stability checking to filter transition/animation frames
  --stability-lookahead MS
                        Milliseconds to look ahead for stability check (default: 200)
  --stability-threshold N
                        Hash difference threshold for stability (default: 5)
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

**Disable all filtering (keep all frames):**
```bash
python video_text_extractor.py video.mp4 --no-deduplicate
```

**Enable blur filtering:**
```bash
python video_text_extractor.py presentation.mp4 --filter-blurry
```

**Filter transition/animation frames (keep only stable images):**
```bash
python video_text_extractor.py presentation.mp4 --check-stability
```

**Complete example with all options:**
```bash
python video_text_extractor.py presentation.mp4 \
  --interval 1000 \
  --deduplicate \
  --filter-blurry \
  --blur-threshold 100 \
  --check-stability \
  --join-char newline \
  --output results.json \
  --images-dir frames
```

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
        "line_height": 28.5,
        "line_count": 1,
        "confidence": 85.5
      },
      {
        "value": "multi-line text\nthat spans multiple lines",
        "x": 100,
        "y": 90,
        "width": 180,
        "height": 65,
        "line_height": 32.0,
        "line_count": 2,
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
  - `width`, `height`: Dimensions of text bounding box (total area including all lines)
  - `line_height`: Average height of individual text lines (useful for multi-line blocks)
  - `line_count`: Number of lines in the text block
  - `confidence`: OCR confidence score (0-100)

**Note:** For multi-line text blocks, `height` represents the total vertical span including line spacing, while `line_height` represents the average height of the actual text lines. Use `line_height` when you need to measure the actual text size regardless of line breaks.

## Utility Scripts

### Filter Text by Height

The `filter_by_height.py` script allows you to parse extraction results and filter text blocks by size:

```bash
# Show text with height >= 50px
python filter_by_height.py output.json 50

# Filter by line height (better for multi-line text)
python filter_by_height.py output.json 40 --use-line-height

# Show detailed information
python filter_by_height.py output.json 50 --details

# Sort by line height
python filter_by_height.py output.json 50 --sort-by line_height

# Export filtered results
python filter_by_height.py output.json 50 --export filtered.json
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

## Transition/Animation Filtering

The stability check feature filters out frames that are part of transitions, animations, or scene changes.

### How It Works

When enabled with `--check-stability`, the script:
1. Captures a frame at timestamp T
2. Looks ahead and captures another frame at timestamp T + lookahead (default: 200ms)
3. Compares the two frames using perceptual hashing
4. If the frames differ significantly (above threshold), the frame is marked as "unstable" and skipped
5. Only frames that remain stable for the lookahead duration are extracted

### Configuration Options

**`--check-stability`**
- Enables the stability check feature

**`--stability-lookahead MS`** (default: 200)
- Milliseconds to look ahead for comparison
- Lower values (100-150): Detect faster transitions, more sensitive
- Higher values (250-500): Only detect longer transitions, less sensitive

**`--stability-threshold N`** (default: 5)
- Maximum hash difference allowed for a frame to be considered "stable"
- Lower values (3-5): Stricter, fewer frames pass as stable
- Higher values (8-15): More permissive, more frames pass as stable


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
2. **Enable deduplication** to reduce OCR workload by skipping identical frames
3. **Enable blur filtering** for better quality results (--filter-blurry)
4. **Lower resolution** videos process faster but may reduce OCR accuracy
5. **Adjust blur threshold** to balance quality and processing time

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
- Enable deduplication (enabled by default)
- Enable blur filtering (--filter-blurry) to skip low-quality frames
- Process smaller section of video for testing
