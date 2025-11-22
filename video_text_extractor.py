#!/usr/bin/env python3
"""
Video Text Extractor - CLI Interface

Command-line interface for extracting text from video recordings using OCR.
"""

import sys
import json
import time
import argparse
import pytesseract
from video_text_lib import extract_frames, extract_text_from_image
from tqdm import tqdm


def main():
    """Main function to orchestrate the video text extraction process."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Extract text from video recordings using OCR',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python video_text_extractor.py presentation.mp4
  python video_text_extractor.py video.mp4 --interval 1000 --output results.json
  python video_text_extractor.py video.mp4 --no-deduplicate --no-filter-blurry
        """
    )
    
    parser.add_argument('video_file', help='Path to input video file')
    parser.add_argument('--interval', type=int, default=500,
                        help='Time interval in milliseconds between frame captures (default: 500)')
    parser.add_argument('--deduplicate', action='store_true', dest='deduplicate', default=True,
                        help='Enable frame deduplication (default)')
    parser.add_argument('--no-deduplicate', action='store_false', dest='deduplicate',
                        help='Disable frame deduplication')
    parser.add_argument('--filter-blurry', action='store_true', dest='filter_blurry', default=False,
                        help='Enable blurry frame filtering')
    parser.add_argument('--no-filter-blurry', action='store_false', dest='filter_blurry',
                        help='Disable blurry frame filtering (default)')
    parser.add_argument('--blur-threshold', type=float, default=100.0,
                        help='Laplacian variance threshold for blur detection (default: 100.0)')
    parser.add_argument('--check-stability', action='store_true', dest='check_stability', default=False,
                        help='Enable stability check to skip frames during transitions/animations')
    parser.add_argument('--stability-threshold', type=int, default=5,
                        help='Max hash difference for frames to be considered stable (default: 5)')
    parser.add_argument('--stability-lookahead', type=int, default=200,
                        help='Milliseconds to look ahead for stability check (default: 200)')
    parser.add_argument('--max-duration', type=int, default=None,
                        help='Maximum duration to process in milliseconds (e.g., 10000 for 10 seconds)')
    parser.add_argument('--join-char', choices=['space', 'newline'], default='space',
                        help='Character to join multi-line text (default: space)')
    parser.add_argument('--output', default='output.json',
                        help='Path for output JSON file (default: output.json)')
    parser.add_argument('--images-dir', default='images',
                        help='Directory to save extracted images (default: images)')
    
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
    
    # Start timing
    start_time = time.time()
    
    print(f"Video Text Extractor")
    print(f"{'=' * 50}")
    print(f"Input video: {args.video_file}")
    print(f"Interval: {args.interval}ms")
    print(f"Deduplication: {'enabled' if args.deduplicate else 'disabled'}")
    print(f"Blur filtering: {'enabled' if args.filter_blurry else 'disabled'}")
    if args.filter_blurry:
        print(f"Blur threshold: {args.blur_threshold}")
    print(f"Stability check: {'enabled' if args.check_stability else 'disabled'}")
    if args.check_stability:
        print(f"Stability threshold: {args.stability_threshold}")
        print(f"Stability lookahead: {args.stability_lookahead}ms")
    if args.max_duration:
        print(f"Max duration: {args.max_duration}ms ({args.max_duration/1000:.1f}s)")
    print(f"Output: {args.output}")
    print(f"Images directory: {args.images_dir}")
    print()
    
    # Step 1: Extract frames
    print("Step 1: Extracting frames from video...")
    try:
        saved_frames, frame_stats = extract_frames(
            args.video_file,
            args.interval,
            args.deduplicate,
            args.filter_blurry,
            args.blur_threshold,
            args.images_dir,
            args.check_stability,
            args.stability_threshold,
            args.stability_lookahead,
            args.max_duration
        )
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    if not saved_frames:
        print("Error: No frames were extracted from the video.", file=sys.stderr)
        sys.exit(1)
    
    print()
    
    # Step 2: Extract text from images
    print("Step 2: Extracting text from images...")
    results = []
    total_text_blocks = 0
    
    for image_path, timestamp_ms in tqdm(saved_frames, desc="Extracting text", unit="image"):
        text_blocks = extract_text_from_image(image_path, args.join_char)
        total_text_blocks += len(text_blocks)
        
        results.append({
            'file': image_path,
            'timestamp_ms': timestamp_ms,
            'text': text_blocks
        })
    
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
    print(f"Frames extracted: {frame_stats['processed']}")
    print(f"Frames skipped (blurry): {frame_stats['blurry']}")
    print(f"Frames skipped (duplicates): {frame_stats['duplicates']}")
    print(f"Frames skipped (unstable): {frame_stats['unstable']}")
    print(f"Total images saved: {frame_stats['saved']}")
    print(f"Output saved to: {args.output}")


if __name__ == "__main__":
    main()
