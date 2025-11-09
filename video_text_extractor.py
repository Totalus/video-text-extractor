#!/usr/bin/env python3
"""
Video Text Extractor - Extract text from video recordings using OCR
"""

import os
import sys
import cv2
import json
import time
import argparse
import numpy as np
from pathlib import Path
from PIL import Image
import pytesseract
from pytesseract import Output
import imagehash
from tqdm import tqdm


def calculate_blur_score(image):
    """
    Calculate blur score using Laplacian variance.
    
    Args:
        image: OpenCV image (BGR format)
        
    Returns:
        float: Laplacian variance (higher = sharper)
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    return laplacian_var


def are_images_similar(hash1, hash2, threshold=5):
    """
    Compare two perceptual hashes to determine if images are similar.
    
    Args:
        hash1: First image hash
        hash2: Second image hash
        threshold: Maximum hash difference for similarity (default: 5)
        
    Returns:
        bool: True if images are similar
    """
    if hash1 is None or hash2 is None:
        return False
    return abs(hash1 - hash2) <= threshold


def extract_frames(video_path, interval_ms, deduplicate, filter_blurry, blur_threshold, images_dir):
    """
    Extract frames from video with optional blur filtering and deduplication.
    
    Args:
        video_path (str): Path to input video file
        interval_ms (int): Time interval in milliseconds between frame captures
        deduplicate (bool): Whether to skip duplicate frames
        filter_blurry (bool): Whether to skip blurry frames
        blur_threshold (float): Laplacian variance threshold for blur detection
        images_dir (str): Directory to save extracted images
        
    Returns:
        list: List of tuples (image_path, timestamp_ms) for saved frames
    """
    # Check if video file exists
    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}", file=sys.stderr)
        sys.exit(1)
    
    # Open video
    video = cv2.VideoCapture(video_path)
    if not video.isOpened():
        print("Error: Cannot open video file. Unsupported format or codec.", file=sys.stderr)
        sys.exit(1)
    
    # Get video properties
    fps = video.get(cv2.CAP_PROP_FPS)
    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_ms = int((total_frames / fps) * 1000) if fps > 0 else 0
    
    # Calculate number of frames to extract
    num_frames_to_extract = (duration_ms // interval_ms) + 1
    
    # Create output directory
    os.makedirs(images_dir, exist_ok=True)
    
    # Initialize tracking variables
    saved_frames = []
    last_hash = None
    stats = {
        'processed': 0,
        'saved': 0,
        'blurry': 0,
        'duplicates': 0
    }
    
    # Progress bar
    pbar = tqdm(total=num_frames_to_extract, desc="Extracting frames", unit="frame")
    
    # Extract frames
    for i in range(num_frames_to_extract):
        timestamp_ms = i * interval_ms
        
        # Set video position
        video.set(cv2.CAP_PROP_POS_MSEC, timestamp_ms)
        success, frame = video.read()
        
        if not success:
            break
        
        stats['processed'] += 1
        
        # Check blur if enabled
        if filter_blurry:
            blur_score = calculate_blur_score(frame)
            if blur_score < blur_threshold:
                stats['blurry'] += 1
                pbar.set_postfix(saved=stats['saved'], blurry=stats['blurry'], duplicates=stats['duplicates'])
                pbar.update(1)
                continue
        
        # Check for duplicates if enabled
        if deduplicate:
            # Convert frame to PIL Image for hashing
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)
            current_hash = imagehash.phash(pil_image)
            
            if are_images_similar(current_hash, last_hash, threshold=5):
                stats['duplicates'] += 1
                pbar.set_postfix(saved=stats['saved'], blurry=stats['blurry'], duplicates=stats['duplicates'])
                pbar.update(1)
                continue
            
            last_hash = current_hash
        
        # Save frame
        filename = f"{timestamp_ms:07d}.png"
        filepath = os.path.join(images_dir, filename)
        cv2.imwrite(filepath, frame)
        
        saved_frames.append((filepath, timestamp_ms))
        stats['saved'] += 1
        
        pbar.set_postfix(saved=stats['saved'], blurry=stats['blurry'], duplicates=stats['duplicates'])
        pbar.update(1)
    
    pbar.close()
    video.release()
    
    return saved_frames, stats


def extract_text_from_image(image_path, join_char):
    """
    Extract text from an image using Tesseract OCR.
    
    Args:
        image_path (str): Path to the image file
        join_char (str): Character to join multi-line text ('space' or 'newline')
        
    Returns:
        list: Array of text objects with position and confidence
    """
    try:
        # Load image
        image = Image.open(image_path)
        
        # Perform OCR
        ocr_data = pytesseract.image_to_data(image, output_type=Output.DICT)
        
        # Extract text blocks
        text_blocks = []
        n_boxes = len(ocr_data['text'])
        
        for i in range(n_boxes):
            confidence = float(ocr_data['conf'][i])
            text = ocr_data['text'][i].strip()
            
            # Filter out low-confidence and empty results
            if confidence < 30 or not text:
                continue
            
            text_blocks.append({
                'value': text,
                'x': int(ocr_data['left'][i]),
                'y': int(ocr_data['top'][i]),
                'width': int(ocr_data['width'][i]),
                'height': int(ocr_data['height'][i]),
                'confidence': round(confidence, 1)
            })
        
        # Sort text blocks top-to-bottom, then left-to-right
        text_blocks.sort(key=lambda b: (b['y'], b['x']))
        
        # Group text blocks that are vertically close and similar size
        grouped_blocks = []
        if text_blocks:
            current_group = [text_blocks[0]]
            
            for i in range(1, len(text_blocks)):
                prev_block = current_group[-1]
                curr_block = text_blocks[i]
                
                # Check if blocks are vertically within 10px
                vertical_distance = abs(curr_block['y'] - prev_block['y'])
                
                # Check if heights are similar (within 20%)
                height_diff = abs(curr_block['height'] - prev_block['height']) / max(prev_block['height'], 1)
                
                if vertical_distance <= 10 and height_diff <= 0.20:
                    current_group.append(curr_block)
                else:
                    # Finalize current group
                    if len(current_group) > 1:
                        # Join the group
                        separator = '\n' if join_char == 'newline' else ' '
                        joined_text = separator.join([b['value'] for b in current_group])
                        
                        # Calculate bounding box for the group
                        min_x = min(b['x'] for b in current_group)
                        min_y = min(b['y'] for b in current_group)
                        max_x = max(b['x'] + b['width'] for b in current_group)
                        max_y = max(b['y'] + b['height'] for b in current_group)
                        avg_conf = sum(b['confidence'] for b in current_group) / len(current_group)
                        
                        grouped_blocks.append({
                            'value': joined_text,
                            'x': min_x,
                            'y': min_y,
                            'width': max_x - min_x,
                            'height': max_y - min_y,
                            'confidence': round(avg_conf, 1)
                        })
                    else:
                        grouped_blocks.append(current_group[0])
                    
                    # Start new group
                    current_group = [curr_block]
            
            # Don't forget the last group
            if len(current_group) > 1:
                separator = '\n' if join_char == 'newline' else ' '
                joined_text = separator.join([b['value'] for b in current_group])
                
                min_x = min(b['x'] for b in current_group)
                min_y = min(b['y'] for b in current_group)
                max_x = max(b['x'] + b['width'] for b in current_group)
                max_y = max(b['y'] + b['height'] for b in current_group)
                avg_conf = sum(b['confidence'] for b in current_group) / len(current_group)
                
                grouped_blocks.append({
                    'value': joined_text,
                    'x': min_x,
                    'y': min_y,
                    'width': max_x - min_x,
                    'height': max_y - min_y,
                    'confidence': round(avg_conf, 1)
                })
            else:
                grouped_blocks.append(current_group[0])
        
        return grouped_blocks
    
    except Exception as e:
        print(f"Warning: OCR failed for {image_path}: {e}", file=sys.stderr)
        return []


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
    parser.add_argument('--filter-blurry', action='store_true', dest='filter_blurry', default=True,
                        help='Enable blurry frame filtering (default)')
    parser.add_argument('--no-filter-blurry', action='store_false', dest='filter_blurry',
                        help='Disable blurry frame filtering')
    parser.add_argument('--blur-threshold', type=float, default=100.0,
                        help='Laplacian variance threshold for blur detection (default: 100.0)')
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
    print(f"Output: {args.output}")
    print(f"Images directory: {args.images_dir}")
    print()
    
    # Step 1: Extract frames
    print("Step 1: Extracting frames from video...")
    saved_frames, frame_stats = extract_frames(
        args.video_file,
        args.interval,
        args.deduplicate,
        args.filter_blurry,
        args.blur_threshold,
        args.images_dir
    )
    
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
    print(f"Total images saved: {frame_stats['saved']}")
    print(f"Text detections: {total_text_blocks}")
    print(f"Output saved to: {args.output}")


if __name__ == "__main__":
    main()
