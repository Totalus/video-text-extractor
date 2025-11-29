#!/usr/bin/env python3
"""
Frame Extractor - Extract frames from video files

Command-line interface for extracting frames from video recordings with
deduplication, blur filtering, and stability checking.
"""

import sys
import json
import time
import argparse
import pytesseract
from video_text_lib import extract_frames


def create_debug_graph(debug_info, output_file='debug_graph.png', settings=None):
    """
    Create a graph showing stability and duplicate scores over time.
    
    Args:
        debug_info: List of frame debug information dictionaries
        output_file: Path to save the graph image
        settings: Optional dict with settings including thresholds
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Warning: matplotlib not installed. Skipping graph generation.", file=sys.stderr)
        print("Install with: pip install matplotlib", file=sys.stderr)
        return
    
    # Extract data from debug_info
    timestamps = []
    stability_scores = []
    duplicate_scores = []
    
    for frame in debug_info:
        timestamps.append(frame['timestamp_ms'])
        # Use None for missing values to avoid plotting them
        stability_scores.append(frame.get('stability_score', None))
        duplicate_scores.append(frame.get('duplicate_score', None))
    
    # Create the plot
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plot stability scores
    ax.plot(timestamps, stability_scores, label='Stability Score', 
            marker='o', linestyle='-', linewidth=2, markersize=4, color='#1f77b4')
    
    # Plot duplicate scores
    ax.plot(timestamps, duplicate_scores, label='Duplicate Score',
            marker='s', linestyle='-', linewidth=2, markersize=4, color='#ff7f0e')
    
    # Add threshold lines if settings are provided
    if settings:
        if timestamps:  # Only draw if we have data
            time_min, time_max = min(timestamps), max(timestamps)
            
            # Stability threshold
            if 'stability_threshold' in settings and settings.get('check_stability', False):
                stability_threshold = settings['stability_threshold']
                ax.axhline(y=stability_threshold, color='#1f77b4', linestyle='--', 
                          linewidth=1.5, alpha=0.7, label=f'Stability Threshold ({stability_threshold})')
            
            # Duplicate threshold
            if settings.get('deduplicate', False) and 'dedupe_threshold' in settings:
                dedupe_threshold = settings['dedupe_threshold']
                ax.axhline(y=dedupe_threshold, color='#ff7f0e', linestyle='--', 
                          linewidth=1.5, alpha=0.7, label=f'Duplicate Threshold ({dedupe_threshold})')
    
    # Customize the plot
    ax.set_xlabel('Timestamp (ms)', fontsize=12)
    ax.set_ylabel('Score', fontsize=12)
    ax.set_title('Frame Analysis: Stability and Duplicate Scores Over Time', fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Add stability lookahead text annotation if available
    if settings and 'stability_lookahead_ms' in settings:
        lookahead = settings['stability_lookahead_ms']
        # Add text box in the top right corner
        textstr = f'Stability Lookahead: {lookahead}ms'
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax.text(0.98, 0.98, textstr, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', horizontalalignment='right', bbox=props)
    
    # Format the plot
    plt.tight_layout()
    
    # Save the plot
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Debug graph saved to: {output_file}")


def main():
    """Main function to extract frames from video."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Extract frames from video recordings',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python extract_frames.py presentation.mp4
  python extract_frames.py video.mp4 --interval 1000 --images-dir frames
  python extract_frames.py video.mp4 --no-deduplicate --no-filter-blurry
  python extract_frames.py video.mp4 --check-stability --stability-threshold 3
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
    parser.add_argument('--threshold', type=int, default=20,
                        help='Hash difference threshold for both deduplication and stability checks (default: 20)')
    parser.add_argument('--check-stability', action='store_true', dest='check_stability', default=True,
                        help='Enable stability check to skip frames during transitions/animations (default)')
    parser.add_argument('--no-check-stability', action='store_false', dest='check_stability',
                        help='Disable stability check')
    parser.add_argument('--stability-lookahead', type=int, default=100,
                        help='Milliseconds to look ahead for stability check (default: 100)')
    parser.add_argument('--max-duration', type=int, default=None,
                        help='Maximum duration to process in milliseconds (e.g., 10000 for 10 seconds)')
    parser.add_argument('--debug', action='store_true', dest='debug', default=False,
                        help='Enable debug mode to save detailed frame information to debug.json')
    parser.add_argument('--images-dir', default='images',
                        help='Directory to save extracted images (default: images)')
    parser.add_argument('--output', default='frames.json',
                        help='Path for output JSON file with frame metadata (default: frames.json)')
    
    args = parser.parse_args()
    
    # Apply --threshold to both dedupe_threshold and stability_threshold
    args.dedupe_threshold = args.threshold
    args.stability_threshold = args.threshold
    
    # Check if Tesseract is installed (required by video_text_lib for image hashing operations)
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
    
    print(f"Frame Extractor")
    print(f"{'=' * 50}")
    print(f"Input video: {args.video_file}")
    print(f"Interval: {args.interval}ms")
    print(f"Threshold: {args.threshold}")
    print(f"Deduplication: {'enabled' if args.deduplicate else 'disabled'}")
    print(f"Blur filtering: {'enabled' if args.filter_blurry else 'disabled'}")
    if args.filter_blurry:
        print(f"Blur threshold: {args.blur_threshold}")
    print(f"Stability check: {'enabled' if args.check_stability else 'disabled'}")
    if args.check_stability:
        print(f"Stability lookahead: {args.stability_lookahead}ms")
    if args.max_duration:
        print(f"Max duration: {args.max_duration}ms ({args.max_duration/1000:.1f}s)")
    print(f"Debug mode: {'enabled' if args.debug else 'disabled'}")
    print(f"Images directory: {args.images_dir}")
    print(f"Output: {args.output}")
    print()
    
    # Extract frames
    print("Extracting frames from video...")
    try:
        saved_frames, frame_stats, debug_info = extract_frames(
            args.video_file,
            args.interval,
            args.deduplicate,
            args.filter_blurry,
            args.blur_threshold,
            args.images_dir,
            args.check_stability,
            args.stability_threshold,
            args.stability_lookahead,
            args.max_duration,
            args.dedupe_threshold,
            args.debug
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
    
    # Save frame metadata JSON
    frame_metadata = []
    for image_path, timestamp_ms in saved_frames:
        frame_metadata.append({
            'file': image_path,
            'timestamp_ms': timestamp_ms
        })
    
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(frame_metadata, f, indent=2, ensure_ascii=False)
    
    # Save debug JSON if debug mode is enabled
    if args.debug and debug_info:
        debug_file = 'debug.json'
        
        # Build debug data structure with metadata
        debug_data = {
            'video_file': args.video_file,
            'settings': {
                'interval_ms': args.interval,
                'threshold': args.threshold,
                'deduplicate': args.deduplicate,
                'dedupe_threshold': args.dedupe_threshold,
                'filter_blurry': args.filter_blurry,
                'blur_threshold': args.blur_threshold,
                'check_stability': args.check_stability,
                'stability_threshold': args.stability_threshold,
                'stability_lookahead_ms': args.stability_lookahead,
                'max_duration_ms': args.max_duration
            },
            'stats': {
                'total_processed': frame_stats['processed'],
                'total_saved': frame_stats['saved'],
                'filtered_blurry': frame_stats['blurry'],
                'filtered_duplicates': frame_stats['duplicates'],
                'filtered_unstable': frame_stats['unstable']
            },
            'frames': debug_info
        }
        
        with open(debug_file, 'w', encoding='utf-8') as f:
            # Write opening brace and metadata
            f.write('{\n')
            f.write('  "video_file": ' + json.dumps(debug_data['video_file']) + ',\n')
            f.write('  "settings": ' + json.dumps(debug_data['settings'], indent=4).replace('\n', '\n  ') + ',\n')
            f.write('  "stats": ' + json.dumps(debug_data['stats'], indent=4).replace('\n', '\n  ') + ',\n')
            f.write('  "frames": [\n')
            
            # Write each frame's debug info on a single line
            for i, frame_debug in enumerate(debug_info):
                line = '    ' + json.dumps(frame_debug, ensure_ascii=False, separators=(',', ': '))
                if i < len(debug_info) - 1:
                    line += ','
                f.write(line + '\n')
            
            # Write closing
            f.write('  ]\n')
            f.write('}\n')
        
        print(f"Debug info saved to: {debug_file}")
        
        # Create debug graph with settings
        create_debug_graph(debug_info, 'debug_graph.png', debug_data['settings'])
    
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
    print(f"Frames processed: {frame_stats['processed']}")
    print(f"Frames skipped (blurry): {frame_stats['blurry']}")
    print(f"Frames skipped (duplicates): {frame_stats['duplicates']}")
    print(f"Frames skipped (unstable): {frame_stats['unstable']}")
    print(f"Total images saved: {frame_stats['saved']}")
    print(f"Frame metadata saved to: {args.output}")


if __name__ == "__main__":
    main()
