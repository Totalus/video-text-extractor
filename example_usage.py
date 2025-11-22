#!/usr/bin/env python3
"""
Example: Using video_text_extractor functions programmatically

This script demonstrates how to import and use the video_text_extractor
functions in your own Python code instead of using the command-line interface.
"""

import json
import sys
from pathlib import Path

# Import functions from the main script
# Note: Ensure video_text_extractor.py is in the same directory or in PYTHONPATH
try:
    from video_text_extractor import (
        extract_frames,
        extract_text_from_image,
        calculate_blur_score,
        are_images_similar
    )
    import cv2
    from PIL import Image
    import imagehash
except ImportError as e:
    print(f"Error importing dependencies: {e}")
    print("Make sure video_text_extractor.py is in the same directory")
    print("and all dependencies are installed (run: pip install -r requirements.txt)")
    sys.exit(1)


def example_basic_usage():
    """Example 1: Basic usage with default settings"""
    print("Example 1: Basic Usage")
    print("-" * 50)
    
    video_path = "sample_video.mp4"
    
    # Extract frames
    frames, stats, _ = extract_frames(
        video_path=video_path,
        interval_ms=500,
        deduplicate=True,
        filter_blurry=True,
        blur_threshold=100.0,
        images_dir="output_images"
    )
    
    print(f"Extracted {len(frames)} frames")
    print(f"Statistics: {stats}")
    
    # Extract text from first frame
    if frames:
        first_frame_path, timestamp = frames[0]
        text_blocks = extract_text_from_image(first_frame_path, join_char='space')
        print(f"\nText from first frame ({timestamp}ms):")
        for block in text_blocks:
            print(f"  - '{block['value']}' (confidence: {block['confidence']})")


def example_custom_processing():
    """Example 2: Custom frame processing with manual filtering"""
    print("\n\nExample 2: Custom Processing")
    print("-" * 50)
    
    video_path = "sample_video.mp4"
    
    # Open video manually for custom processing
    video = cv2.VideoCapture(video_path)
    if not video.isOpened():
        print(f"Cannot open video: {video_path}")
        return
    
    # Process specific frames
    frames_to_check = [0, 1000, 2000, 3000]  # milliseconds
    
    for timestamp_ms in frames_to_check:
        video.set(cv2.CAP_PROP_POS_MSEC, timestamp_ms)
        success, frame = video.read()
        
        if success:
            # Check blur score
            blur_score = calculate_blur_score(frame)
            print(f"\nFrame at {timestamp_ms}ms - Blur score: {blur_score:.2f}")
            
            if blur_score >= 100:
                print("  ✓ Frame is sharp enough")
            else:
                print("  ✗ Frame is too blurry")
    
    video.release()


def example_image_comparison():
    """Example 3: Compare two images for similarity"""
    print("\n\nExample 3: Image Similarity Comparison")
    print("-" * 50)
    
    # This example requires two image files
    image1_path = "output_images/0000000.png"
    image2_path = "output_images/0000500.png"
    
    try:
        # Load images and calculate hashes
        img1 = Image.open(image1_path)
        img2 = Image.open(image2_path)
        
        hash1 = imagehash.phash(img1)
        hash2 = imagehash.phash(img2)
        
        # Calculate difference
        difference = abs(hash1 - hash2)
        
        print(f"Image 1: {image1_path}")
        print(f"Image 2: {image2_path}")
        print(f"Hash difference: {difference}")
        
        if are_images_similar(hash1, hash2, threshold=5):
            print("✓ Images are similar (difference <= 5)")
        else:
            print("✗ Images are different (difference > 5)")
            
    except FileNotFoundError as e:
        print(f"Images not found: {e}")
        print("Run example_basic_usage() first to generate images")


def example_batch_processing():
    """Example 4: Process multiple videos in batch"""
    print("\n\nExample 4: Batch Processing")
    print("-" * 50)
    
    videos = [
        "video1.mp4",
        "video2.mp4",
        "video3.mp4"
    ]
    
    results = []
    
    for video_path in videos:
        print(f"\nProcessing: {video_path}")
        
        try:
            # Extract frames
            frames, stats, _ = extract_frames(
                video_path=video_path,
                interval_ms=1000,
                deduplicate=True,
                filter_blurry=True,
                blur_threshold=100.0,
                images_dir=f"output_{Path(video_path).stem}"
            )
            
            # Extract text from all frames
            video_results = []
            for frame_path, timestamp in frames:
                text_blocks = extract_text_from_image(frame_path, join_char='space')
                video_results.append({
                    'file': frame_path,
                    'timestamp_ms': timestamp,
                    'text': text_blocks
                })
            
            results.append({
                'video': video_path,
                'frames_extracted': len(frames),
                'stats': stats,
                'data': video_results
            })
            
            print(f"  ✓ Extracted {len(frames)} frames")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    # Save combined results
    output_file = "batch_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Batch processing complete. Results saved to: {output_file}")


def example_filtered_text_extraction():
    """Example 5: Extract only high-confidence text"""
    print("\n\nExample 5: High-Confidence Text Only")
    print("-" * 50)
    
    video_path = "sample_video.mp4"
    min_confidence = 80.0  # Only accept text with 80%+ confidence
    
    # Extract frames
    frames, stats, _ = extract_frames(
        video_path=video_path,
        interval_ms=500,
        deduplicate=True,
        filter_blurry=True,
        blur_threshold=100.0,
        images_dir="filtered_output"
    )
    
    high_confidence_text = []
    
    for frame_path, timestamp in frames:
        text_blocks = extract_text_from_image(frame_path, join_char='space')
        
        # Filter by confidence
        for block in text_blocks:
            if block['confidence'] >= min_confidence:
                high_confidence_text.append({
                    'text': block['value'],
                    'confidence': block['confidence'],
                    'timestamp_ms': timestamp,
                    'frame': frame_path
                })
    
    print(f"Found {len(high_confidence_text)} high-confidence text blocks:")
    for item in high_confidence_text[:10]:  # Show first 10
        print(f"  [{item['timestamp_ms']}ms] {item['text']} ({item['confidence']}%)")
    
    if len(high_confidence_text) > 10:
        print(f"  ... and {len(high_confidence_text) - 10} more")


if __name__ == "__main__":
    print("Video Text Extractor - Programmatic Usage Examples")
    print("=" * 50)
    print()
    print("Note: These examples require sample video files.")
    print("Modify the file paths to match your actual video files.")
    print()
    
    # Uncomment the examples you want to run:
    
    # example_basic_usage()
    # example_custom_processing()
    # example_image_comparison()
    # example_batch_processing()
    # example_filtered_text_extraction()
    
    print("\nTo run examples, uncomment the function calls at the end of this script.")
