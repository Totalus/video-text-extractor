#!/usr/bin/env python3
"""
Video Text Extractor - Backward Compatibility Wrapper

This script maintains backward compatibility by importing from the new modular structure.
For library usage, import from video_text_lib directly.
For CLI usage, use cli.py or this wrapper script.
"""

from cli import main

if __name__ == "__main__":
    main()
