#!/usr/bin/env python3
"""
Subana - Subtitle & Cue Extractor
A modular application for extracting and exporting subtitles from JSON files.

Usage:
    python subana.py
    or
    python -m subana
"""

import sys
import os

# Add current directory to path to ensure imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui import run


def main():
    """Main entry point for Subana application"""
    try:
        run()
    except KeyboardInterrupt:
        print("\nApplication terminated by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error running application: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
