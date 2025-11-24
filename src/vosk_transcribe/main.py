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

import vosk
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
        # Resolve the provided model path
        resolved_path = model_manager.resolve_model_path(model_path)
    else:
        # Try to find a default model
        available_models = model_manager.list_available_models()
        if not available_models:
            raise RuntimeError(
                "No models found. Please download a model first using vosk-download-model-1000"
            )
        # Use the first available model as default
        resolved_path = model_manager.resolve_model_path(available_models[0])

    # Load the model
    model = vosk.Model(str(resolved_path))

    # Get model sample rate
    model_sample_rate = model_manager.get_model_sample_rate(str(resolved_path))

    # Initialize Vosk recognizer
    rec = vosk.KaldiRecognizer(model, model_sample_rate)

    # Read and transcribe the audio file
    print(f"Transcribing: {audio_file}", file=sys.stderr)

    import wave
    import json

    # Open the audio file
    wf = wave.open(audio_file, "rb")
    if (
        wf.getnchannels() != 1
        or wf.getsampwidth() != 2
        or wf.getframerate() != model_sample_rate
    ):
        print(
            f"Audio file must be WAV format mono PCM at {model_sample_rate}Hz",
            file=sys.stderr,
        )
        sys.exit(1)

    # Process the audio in chunks
    transcription = ""
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            transcription += result.get("text", "") + " "

    # Get final result
    result = json.loads(rec.FinalResult())
    transcription += result.get("text", "")

    wf.close()

    transcription = transcription.strip()
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
