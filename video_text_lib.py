#!/usr/bin/env python3
"""
Video Text Extraction Library

This module provides core functionality for extracting frames from videos
and performing OCR text extraction. Can be used as a library or via CLI.
"""

import os
import sys
import cv2
import numpy as np
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
        tuple: (saved_frames, stats)
            - saved_frames: List of tuples (image_path, timestamp_ms) for saved frames
            - stats: Dictionary with extraction statistics
    """
    # Check if video file exists
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    # Open video
    video = cv2.VideoCapture(video_path)
    if not video.isOpened():
        raise ValueError("Cannot open video file. Unsupported format or codec.")
    
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
    
    # Extract frames at intervals
    timestamp_ms = 0
    while timestamp_ms <= duration_ms:
        # Set video position
        video.set(cv2.CAP_PROP_POS_MSEC, timestamp_ms)
        success, frame = video.read()
        
        if not success:
            break
        
        stats['processed'] += 1
        
        # Check blur
        if filter_blurry:
            blur_score = calculate_blur_score(frame)
            if blur_score < blur_threshold:
                stats['blurry'] += 1
                pbar.set_postfix_str(f"{stats['saved']} saved | {stats['blurry']} blurry | {stats['duplicates']} duplicates | {stats['unstable']} unstable")
                pbar.update(1)
                timestamp_ms += interval_ms
                continue
        
        # Calculate hash for deduplication and stability check
        frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        current_hash = imagehash.phash(frame_pil)
        
        # Check deduplication
        if deduplicate and are_images_similar(current_hash, last_hash):
            stats['duplicates'] += 1
            pbar.set_postfix_str(f"{stats['saved']} saved | {stats['blurry']} blurry | {stats['duplicates']} duplicates | {stats['unstable']} unstable")
            pbar.update(1)
            timestamp_ms += interval_ms
            continue
        
        # Check stability (if enabled)
        is_stable = True
        stability_score = 0
        if check_stability:
            # Get frame at lookahead position
            lookahead_timestamp = timestamp_ms + stability_lookahead_ms
            video.set(cv2.CAP_PROP_POS_MSEC, lookahead_timestamp)
            success_lookahead, frame_lookahead = video.read()
            
            if success_lookahead:
                frame_lookahead_pil = Image.fromarray(cv2.cvtColor(frame_lookahead, cv2.COLOR_BGR2RGB))
                lookahead_hash = imagehash.phash(frame_lookahead_pil)
                stability_score = abs(current_hash - lookahead_hash)
                
                if stability_score > stability_threshold:
                    is_stable = False
                    stats['unstable'] += 1
                    pbar.set_postfix_str(f"{stats['saved']} saved | {stats['blurry']} blurry | {stats['duplicates']} duplicates | {stats['unstable']} unstable")
                    pbar.update(1)
                    timestamp_ms += interval_ms
                    continue
        
        # Save frame
        if check_stability:
            stability_label = "stable" if is_stable else "unstable"
            image_filename = f"{timestamp_ms:07d}_s{stability_score}_{stability_label}.png"
        else:
            image_filename = f"{timestamp_ms:07d}.png"
        
        image_path = os.path.join(images_dir, image_filename)
        cv2.imwrite(image_path, frame)
        
        saved_frames.append((image_path, timestamp_ms))
        stats['saved'] += 1
        last_hash = current_hash
        
        pbar.set_postfix_str(f"{stats['saved']} saved | {stats['blurry']} blurry | {stats['duplicates']} duplicates | {stats['unstable']} unstable")
        pbar.update(1)
        
        timestamp_ms += interval_ms
    
    pbar.close()
    video.release()
    
    return saved_frames, stats


def extract_text_from_image(image_path, join_char='space'):
    """
    Extract text from an image using OCR with intelligent grouping.
    
    Groups text blocks into lines (horizontal) and then multi-line blocks (vertical).
    Uses a clustering approach to handle variable baselines and text positions.
    
    Args:
        image_path (str): Path to image file
        join_char (str): 'space' or 'newline' to join multi-line text
        
    Returns:
        list: List of dictionaries containing text blocks with position and confidence
    """
    try:
        # Load image
        img = Image.open(image_path)
        
        # Perform OCR
        ocr_data = pytesseract.image_to_data(img, output_type=Output.DICT)
        
        # Filter and collect high-confidence text blocks
        n_boxes = len(ocr_data['text'])
        raw_blocks = []
        
        for i in range(n_boxes):
            confidence = float(ocr_data['conf'][i])
            text = ocr_data['text'][i].strip()
            
            # Filter out low confidence and empty text
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
                'blocks': line_blocks,
                'avg_confidence': sum(b['confidence'] for b in line_blocks) / len(line_blocks)
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
                'confidence': sum(line['avg_confidence'] for line in block_lines) / len(block_lines)
            })
        
        return final_blocks
        
    except Exception as e:
        print(f"Warning: OCR failed for {image_path}: {e}", file=sys.stderr)
        return []
