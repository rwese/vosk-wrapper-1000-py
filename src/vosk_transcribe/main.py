"""
Vosk Transcribe - Standalone file transcription tool.

This tool provides command-line audio file transcription using Vosk.
"""

import argparse
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from vosk_core.model_manager import ModelManager
from vosk_core.audio_processor import AudioProcessor


def transcribe_file(
    audio_file: str, model_path: str = None, output_file: str = None
) -> str:
    """
    Transcribe an audio file using Vosk.

    Args:
        audio_file: Path to the audio file to transcribe
        model_path: Path to the Vosk model (optional, will use default if not provided)
        output_file: Path to save transcription (optional, prints to stdout if not provided)

    Returns:
        The transcription text
    """
    if not os.path.exists(audio_file):
        raise FileNotFoundError(f"Audio file not found: {audio_file}")

    # Initialize model manager
    model_manager = ModelManager()
    if model_path:
        model = model_manager.load_model(model_path)
    else:
        # Try to find a default model
        model_dir = model_manager.get_default_model_dir()
        if not model_dir.exists():
            raise RuntimeError(
                "No model found. Please download a model first or specify --model"
            )
        model = model_manager.load_model_from_dir(str(model_dir))

    # Initialize audio processor
    audio_processor = AudioProcessor(model)

    # Transcribe the file
    print(f"Transcribing: {audio_file}", file=sys.stderr)
    transcription = audio_processor.transcribe_file(audio_file)
    print(f"Transcription complete", file=sys.stderr)

    # Output the result
    if output_file:
        with open(output_file, "w") as f:
            f.write(transcription)
        print(f"Transcription saved to: {output_file}", file=sys.stderr)
    else:
        print(transcription)

    return transcription


__all__ = ["main", "transcribe_file"]


def main():
    """Main entry point for the transcribe tool."""
    parser = argparse.ArgumentParser(
        description="Transcribe audio files using Vosk speech recognition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  vosk-transcribe audio.wav
  vosk-transcribe audio.wav --model /path/to/model --output transcript.txt
  vosk-transcribe audio.mp3 --output result.txt
        """,
    )

    parser.add_argument("audio_file", help="Path to the audio file to transcribe")

    parser.add_argument(
        "--model",
        "-m",
        help="Path to the Vosk model directory (optional, uses default if not specified)",
    )

    parser.add_argument(
        "--output",
        "-o",
        help="Output file to save transcription (optional, prints to stdout if not specified)",
    )

    args = parser.parse_args()

    try:
        transcribe_file(args.audio_file, args.model, args.output)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
