#!/usr/bin/env python3
"""
Text Extractor - Extract text from image frames using OCR

Command-line interface for extracting text from image frames using Tesseract OCR.
"""

import sys
import json
import time
import os
import glob
import argparse
import pytesseract
from video_text_lib import extract_text_from_image
from tqdm import tqdm


def main():
    """Main function to extract text from image frames."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Extract text from image frames using OCR',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python extract_text.py frames/
  python extract_text.py frames/ --output text_results.json
  python extract_text.py frames/ --join-char newline
  python extract_text.py frames/ --frames-metadata frames.json
        """
    )
    
    parser.add_argument('images_dir', help='Directory containing image frames (PNG files)')
    parser.add_argument('--join-char', choices=['space', 'newline'], default='space',
                        help='Character to join multi-line text (default: space)')
    parser.add_argument('--output', default='output.json',
                        help='Path for output JSON file (default: output.json)')
    parser.add_argument('--frames-metadata', default=None,
                        help='Optional JSON file with frame metadata (from extract_frames.py) to include timestamps')
    
    args = parser.parse_args()
    
    # Check if Tesseract is installed
    try:
        pytesseract.get_tesseract_version()
    except pytesseract.TesseractNotFoundError:
        print("Error: Tesseract is not installed. Please install it first.", file=sys.stderr)
        print("  Linux:   sudo apt-get install tesseract-ocr", file=sys.stderr)
        print("  macOS:   brew install tesseract", file=sys.stderr)
        print("  Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki", file=sys.stderr)
        sys.exit(1)
    
    # Check if images directory exists
    if not os.path.exists(args.images_dir):
        print(f"Error: Directory not found: {args.images_dir}", file=sys.stderr)
        sys.exit(1)
    
    if not os.path.isdir(args.images_dir):
        print(f"Error: Not a directory: {args.images_dir}", file=sys.stderr)
        sys.exit(1)
    
    # Load frame metadata if provided
    frame_metadata_map = {}
    if args.frames_metadata:
        if not os.path.exists(args.frames_metadata):
            print(f"Warning: Frame metadata file not found: {args.frames_metadata}", file=sys.stderr)
        else:
            try:
                with open(args.frames_metadata, 'r', encoding='utf-8') as f:
                    frames_data = json.load(f)
                    # Build a map from filename to metadata
                    for frame in frames_data:
                        filename = os.path.basename(frame['file'])
                        frame_metadata_map[filename] = frame
            except Exception as e:
                print(f"Warning: Could not load frame metadata: {e}", file=sys.stderr)
    
    # Find all PNG files in the directory
    image_pattern = os.path.join(args.images_dir, "*.png")
    image_files = sorted(glob.glob(image_pattern))
    
    if not image_files:
        print(f"Error: No PNG files found in directory: {args.images_dir}", file=sys.stderr)
        sys.exit(1)
    
    # Start timing
    start_time = time.time()
    
    print(f"Text Extractor")
    print(f"{'=' * 50}")
    print(f"Images directory: {args.images_dir}")
    print(f"Images found: {len(image_files)}")
    print(f"Join character: {args.join_char}")
    print(f"Output: {args.output}")
    if args.frames_metadata:
        print(f"Frame metadata: {args.frames_metadata} ({len(frame_metadata_map)} entries loaded)")
    print()
    
    # Extract text from images
    print("Extracting text from images...")
    results = []
    total_text_blocks = 0
    
    for image_path in tqdm(image_files, desc="Extracting text", unit="image"):
        text_blocks = extract_text_from_image(image_path, args.join_char)
        total_text_blocks += len(text_blocks)
        
        # Get metadata for this frame if available
        filename = os.path.basename(image_path)
        frame_metadata = frame_metadata_map.get(filename, {})
        
        result = {
            'file': image_path,
            'text': text_blocks
        }
        
        # Add timestamp if available from metadata
        if 'timestamp_ms' in frame_metadata:
            result['timestamp_ms'] = frame_metadata['timestamp_ms']
        
        results.append(result)
    
    # Save output JSON
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Calculate execution time
    end_time = time.time()
    execution_time = end_time - start_time
    
    # Display final statistics
    print()
    print(f"{'=' * 50}")
    print("=== Extraction Complete ===")
    print(f"{'=' * 50}")
    
    # Format time
    if execution_time < 60:
        time_str = f"{execution_time:.1f}s"
    else:
        minutes = int(execution_time // 60)
        seconds = int(execution_time % 60)
        time_str = f"{minutes}m {seconds}s"
    
    print(f"Total time: {time_str}")
    print(f"Images processed: {len(image_files)}")
    print(f"Text blocks extracted: {total_text_blocks}")
    print(f"Average blocks per image: {total_text_blocks / len(image_files):.1f}")
    print(f"Output saved to: {args.output}")


if __name__ == "__main__":
    main()
