# Video Text Extractor

A Python tool that extracts images from video recordings and uses OCR (Optical Character Recognition) technology to extract texts from those images. The tool consists of two separate scripts that can be used independently or together:

1. **`extract_frames.py`** - Extracts frames from videos with intelligent filtering
2. **`extract_text.py`** - Performs OCR on extracted frames to detect text

## AI Usage Disclamer

I value transparency in the use of AI tool and find my responsability to indicate when AI tool was significantly used in my projects.

This tool vibe coded using Claude Sonnet 4.5.

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
- Tesseract OCR (must be installed separately) for text extraction

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

## Frame exraction

The `extract_frames.py` script is used to extract frames (as images) from a video at a fixed interval of time (ex: each 500 ms). By default, the script will filter out images that are transitioning (unsable) and images that are duplicate (same as previous image).

To decide whether an image is a duplicate, we compare the current frame (using a perceptive hashing) to the previous saved frame. If the perceptive hash are similar (difference is lower than a certain threshold), we ignore the second image as duplicate of the previous saved image.

To figure out if an image is static or transitioning (unstable), we look at the frame that occurs after a certain delay (called the *stability lookahead*) ahead of the current frame. Using perceptive hash again, we compare both images. If the are too different (difference of their perceptive hash lower than a certain threshold), it means the frame is transitioning, so we ignore it. We only keep frames that are *stable* (not in a transition).

Those two filtering options are enabled by default. They can be disabled: running `./extract_frames.py --no-deduplicate --no-check-stability --interval 100` will keep all frames at 100 ms interval.

### Tweaking your params for better results

The first param to adjust would be the interval at which the frames are extracted (`--interval`). A bigger interval will extract the frames faster, but might skip some of the frames you want to export. A shorter interval will take longer, but will skip less frames.

The threshold of comparison for deduplication and stability check can be also be adjusted (using the `--threshold` option) if the default values do not perform well for your use case.

The `--debug` option is handy to help you analyze and tweak the params if needed. It will save all the frames, but add a `-r` suffix to the ones that would normally be ignored. It will also calculate the stability and deduplication score (hash difference) and save the info in a `debug.json` file. A graph of those scores will also be saved so you can visually take a look. You can use the `--start-time` and `--stop-time` params to only process a specific time range of the input video (useful for long recordings).

Use `python extract_frames.py --help` for more usage information.

