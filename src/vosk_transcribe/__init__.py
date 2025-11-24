"""
Vosk Transcribe - Standalone file transcription tool.

This tool provides command-line audio file transcription using Vosk.
"""

from .main import main, transcribe_file

__all__ = ["main", "transcribe_file"]
