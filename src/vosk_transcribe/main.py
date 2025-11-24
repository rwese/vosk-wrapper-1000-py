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

    Supports WAV files with automatic conversion to mono and resampling to match the model's sample rate.

    Args:
        audio_file: Path to the WAV audio file to transcribe (must be 16-bit)
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
    import numpy as np

    # Open the audio file
    wf = wave.open(audio_file, "rb")

    # Get audio file properties
    channels = wf.getnchannels()
    sampwidth = wf.getsampwidth()
    framerate = wf.getframerate()
    nframes = wf.getnframes()

    print(f"Input file: {audio_file}", file=sys.stderr)
    print(f"  Channels: {channels}", file=sys.stderr)
    print(f"  Sample width: {sampwidth} bytes", file=sys.stderr)
    print(f"  Sample rate: {framerate} Hz", file=sys.stderr)
    print(f"  Duration: {nframes / framerate:.2f} seconds", file=sys.stderr)

    if sampwidth != 2:
        print(
            f"Error: Only 16-bit (2 byte) WAV files are supported",
            file=sys.stderr,
        )
        sys.exit(1)

    if channels > 1:
        print(
            f"  Note: Converting {channels}-channel audio to mono",
            file=sys.stderr,
        )

    # Initialize audio processor for resampling if needed
    audio_processor = AudioProcessor(
        device_rate=framerate,
        model_rate=model_sample_rate,
        noise_filter_enabled=False,  # Disable noise reduction for simple transcribe
        silence_threshold=50.0,  # Default silence threshold
        normalize_audio=False,  # Disable normalization for simple transcribe
        pre_roll_duration=0.0,  # No pre-roll for file transcribe
        vad_hysteresis_chunks=1,  # Minimal VAD for file transcribe
    )

    print(
        f"Processing audio (model expects {model_sample_rate} Hz)...",
        file=sys.stderr,
    )

    # Process the audio in chunks
    transcription = ""
    chunk_size = 4000  # Process 4000 frames at a time

    while True:
        data = wf.readframes(chunk_size)
        if len(data) == 0:
            break

        # Convert bytes to numpy array
        audio_chunk = np.frombuffer(data, dtype=np.int16)

        # Convert to mono first (silence detection must be done before other processing)
        if channels > 1:
            # Reshape interleaved multi-channel data to (frames, channels)
            frames = len(audio_chunk) // channels
            audio_multi = audio_chunk.reshape(frames, channels)
            # Average all channels to create mono
            mono_chunk = np.mean(audio_multi, axis=1).astype(np.int16)
        else:
            mono_chunk = audio_chunk

        # Process audio through pipeline (resampling if needed)
        processed_audio = audio_processor._process_mono_audio_chunk(mono_chunk)

        # Send to Vosk
        if rec.AcceptWaveform(bytes(processed_audio)):
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
  vosk-transcribe audio.wav --model vosk-model-en-us-0.22 --output transcript.txt

Supported formats:
  - WAV files (16-bit PCM)
  - Automatic mono conversion from stereo/multi-channel
  - Automatic resampling to match model sample rate
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
