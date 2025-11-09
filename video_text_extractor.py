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


def extract_frames(video_path, interval_ms, deduplicate, filter_blurry, blur_threshold, images_dir, 
                   check_stability=False, stability_threshold=5, stability_lookahead_ms=200):
    """
    Extract frames from video with optional blur filtering and deduplication.
    
    Args:
        video_path (str): Path to input video file
        interval_ms (int): Time interval in milliseconds between frame captures
        deduplicate (bool): Whether to skip duplicate frames
        filter_blurry (bool): Whether to skip blurry frames
        blur_threshold (float): Laplacian variance threshold for blur detection
        images_dir (str): Directory to save extracted images
        check_stability (bool): Whether to check if frame is stable (not in transition)
        stability_threshold (int): Max hash difference for frames to be considered stable
        stability_lookahead_ms (int): How many ms ahead to check for stability
        
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
        'duplicates': 0,
        'unstable': 0
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
                pbar.set_postfix(saved=stats['saved'], blurry=stats['blurry'], 
                                duplicates=stats['duplicates'], unstable=stats['unstable'])
                pbar.update(1)
                continue
        
        # Convert frame to PIL Image for hashing (used by multiple checks)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(frame_rgb)
        current_hash = imagehash.phash(pil_image)
        
        # Check stability if enabled (do this before deduplication)
        if check_stability:
            # Look ahead to see if the frame is stable
            lookahead_timestamp = timestamp_ms + stability_lookahead_ms
            video.set(cv2.CAP_PROP_POS_MSEC, lookahead_timestamp)
            success_lookahead, frame_lookahead = video.read()
            
            if success_lookahead:
                # Calculate hash of lookahead frame
                frame_lookahead_rgb = cv2.cvtColor(frame_lookahead, cv2.COLOR_BGR2RGB)
                pil_image_lookahead = Image.fromarray(frame_lookahead_rgb)
                lookahead_hash = imagehash.phash(pil_image_lookahead)
                
                # If frames are too different, we're in a transition
                if not are_images_similar(current_hash, lookahead_hash, threshold=stability_threshold):
                    stats['unstable'] += 1
                    pbar.set_postfix(saved=stats['saved'], blurry=stats['blurry'], 
                                    duplicates=stats['duplicates'], unstable=stats['unstable'])
                    pbar.update(1)
                    continue
        
        # Check for duplicates if enabled
        if deduplicate:
            if are_images_similar(current_hash, last_hash, threshold=5):
                stats['duplicates'] += 1
                pbar.set_postfix(saved=stats['saved'], blurry=stats['blurry'], 
                                duplicates=stats['duplicates'], unstable=stats['unstable'])
                pbar.update(1)
                continue
            
            last_hash = current_hash
        
        # Save frame
        filename = f"{timestamp_ms:07d}.png"
        filepath = os.path.join(images_dir, filename)
        cv2.imwrite(filepath, frame)
        
        saved_frames.append((filepath, timestamp_ms))
        stats['saved'] += 1
        
        pbar.set_postfix(saved=stats['saved'], blurry=stats['blurry'], 
                        duplicates=stats['duplicates'], unstable=stats['unstable'])
        pbar.update(1)
    
    pbar.close()
    video.release()
    
    return saved_frames, stats


def extract_text_from_image(image_path, join_char):
    """
    Extract text from an image using Tesseract OCR with improved grouping.
    
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
        
        # Extract raw text blocks (only high confidence)
        raw_blocks = []
        n_boxes = len(ocr_data['text'])
        
        for i in range(n_boxes):
            confidence = float(ocr_data['conf'][i])
            text = ocr_data['text'][i].strip()
            
            # Filter out low-confidence and empty results
            if confidence < 70 or not text:
                continue
            
            raw_blocks.append({
                'value': text,
                'x': int(ocr_data['left'][i]),
                'y': int(ocr_data['top'][i]),
                'width': int(ocr_data['width'][i]),
                'height': int(ocr_data['height'][i]),
                'confidence': round(confidence, 1)
            })
        
        if not raw_blocks:
            return []
        
        # STAGE 1: Group blocks into lines (horizontal alignment)
        # Use a smarter clustering approach instead of simple sorting
        lines = []
        used_blocks = set()
        
        # Sort blocks by x position for initial scanning
        blocks_by_x = sorted(enumerate(raw_blocks), key=lambda b: b[1]['x'])
        
        for idx, seed_block in blocks_by_x:
            if idx in used_blocks:
                continue
            
            # Start a new line with this seed block
            current_line = [seed_block]
            used_blocks.add(idx)
            
            # Find all other blocks that belong to this line
            # Scan through remaining blocks and check if they're on the same line
            for j, candidate in enumerate(raw_blocks):
                if j in used_blocks:
                    continue
                
                # Check if candidate can join any block already in the current line
                can_join = False
                for line_block in current_line:
                    # Check vertical alignment (do they overlap vertically or are close?)
                    vertical_distance = abs(candidate['y'] - line_block['y'])
                    height_ratio = max(candidate['height'], line_block['height']) / min(candidate['height'], line_block['height'])
                    
                    # Calculate horizontal position relationship
                    candidate_left = candidate['x']
                    candidate_right = candidate['x'] + candidate['width']
                    line_block_left = line_block['x']
                    line_block_right = line_block['x'] + line_block['width']
                    
                    # Check if they're horizontally near each other
                    horizontal_gap = min(
                        abs(candidate_left - line_block_right),
                        abs(line_block_left - candidate_right)
                    )
                    
                    # Same line if: vertically aligned, similar height, horizontally close
                    if vertical_distance <= 10 and height_ratio <= 1.5 and horizontal_gap < 100:
                        can_join = True
                        break
                
                if can_join:
                    current_line.append(candidate)
                    used_blocks.add(j)
            
            # Sort blocks in this line from left to right
            current_line.sort(key=lambda b: b['x'])
            lines.append(current_line)
        
        # Sort lines from top to bottom (by minimum y position)
        lines.sort(key=lambda line: min(b['y'] for b in line))
        
        # Convert lines to line objects with combined bounding box
        line_objects = []
        for line_blocks in lines:
            # Calculate bounding box for entire line
            min_x = min(b['x'] for b in line_blocks)
            min_y = min(b['y'] for b in line_blocks)
            max_x = max(b['x'] + b['width'] for b in line_blocks)
            max_y = max(b['y'] + b['height'] for b in line_blocks)
            
            # Sort blocks in line from left to right
            line_blocks.sort(key=lambda b: b['x'])
            
            # Join text with spaces
            line_text = ' '.join(b['value'] for b in line_blocks)
            
            line_objects.append({
                'value': line_text,
                'x': min_x,
                'y': min_y,
                'width': max_x - min_x,
                'height': max_y - min_y,
                'confidence': round(sum(b['confidence'] for b in line_blocks) / len(line_blocks), 1)
            })
        
        # STAGE 2: Group lines into multi-line blocks (vertical stacking)
        final_blocks = []
        used_lines = set()
        
        for i, line in enumerate(line_objects):
            if i in used_lines:
                continue
            
            # Start a new multi-line block
            block_lines = [line]
            used_lines.add(i)
            
            # Look for lines below that should be grouped
            for j in range(i + 1, len(line_objects)):
                if j in used_lines:
                    continue
                
                next_line = line_objects[j]
                last_line = block_lines[-1]
                
                # Check if next line should be grouped with current block
                vertical_gap = next_line['y'] - (last_line['y'] + last_line['height'])
                
                # Check horizontal overlap (lines must be vertically aligned)
                last_line_left = last_line['x']
                last_line_right = last_line['x'] + last_line['width']
                next_line_left = next_line['x']
                next_line_right = next_line['x'] + next_line['width']
                
                # Calculate overlap
                overlap_left = max(last_line_left, next_line_left)
                overlap_right = min(last_line_right, next_line_right)
                horizontal_overlap = max(0, overlap_right - overlap_left)
                
                # Require at least some horizontal overlap for multi-line grouping
                min_width = min(last_line['width'], next_line['width'])
                has_overlap = horizontal_overlap > 0
                
                # Check height similarity (prevent grouping very different sizes)
                height_ratio = max(next_line['height'], last_line['height']) / min(next_line['height'], last_line['height'])
                
                # Group if: close vertically, have horizontal overlap, and similar heights
                if vertical_gap <= 15 and has_overlap and height_ratio <= 1.5:
                    block_lines.append(next_line)
                    used_lines.add(j)
                else:
                    # Too far apart or not aligned, stop looking
                    break
            
            # Create final block
            min_x = min(line['x'] for line in block_lines)
            min_y = min(line['y'] for line in block_lines)
            max_x = max(line['x'] + line['width'] for line in block_lines)
            max_y = max(line['y'] + line['height'] for line in block_lines)
            
            # Join lines with specified separator
            separator = '\n' if join_char == 'newline' else ' '
            block_text = separator.join(line['value'] for line in block_lines)
            
            final_blocks.append({
                'value': block_text,
                'x': min_x,
                'y': min_y,
                'width': max_x - min_x,
                'height': max_y - min_y,
                'confidence': round(sum(line['confidence'] for line in block_lines) / len(block_lines), 1)
            })
        
        return final_blocks
    
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
    parser.add_argument('--check-stability', action='store_true', dest='check_stability', default=False,
                        help='Enable stability check to skip frames during transitions/animations')
    parser.add_argument('--stability-threshold', type=int, default=5,
                        help='Max hash difference for frames to be considered stable (default: 5)')
    parser.add_argument('--stability-lookahead', type=int, default=200,
                        help='Milliseconds to look ahead for stability check (default: 200)')
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
        args.images_dir,
        args.check_stability,
        args.stability_threshold,
        args.stability_lookahead
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
    print(f"Frames skipped (unstable): {frame_stats['unstable']}")
    print(f"Total images saved: {frame_stats['saved']}")
    # print(f"Text detections: {total_text_blocks}")
    print(f"Output saved to: {args.output}")


if __name__ == "__main__":
    main()
