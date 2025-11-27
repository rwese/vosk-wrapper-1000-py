import argparse
import os
import shutil
import sys
import zipfile
from pathlib import Path

import requests
from tqdm import tqdm

from vosk_core.xdg_paths import get_default_model_path, get_models_dir

MODEL_LIST_URL = "https://alphacephei.com/vosk/models/model-list.json"
DEFAULT_OUTPUT_DIR = str(get_models_dir())

# FasterWhisper available models
FASTER_WHISPER_MODELS = [
    {"name": "tiny", "size": "~75 MB", "lang": "Multilingual"},
    {"name": "tiny.en", "size": "~75 MB", "lang": "English only"},
    {"name": "base", "size": "~150 MB", "lang": "Multilingual"},
    {"name": "base.en", "size": "~150 MB", "lang": "English only"},
    {"name": "small", "size": "~500 MB", "lang": "Multilingual"},
    {"name": "small.en", "size": "~500 MB", "lang": "English only"},
    {"name": "medium", "size": "~1.5 GB", "lang": "Multilingual"},
    {"name": "medium.en", "size": "~1.5 GB", "lang": "English only"},
    {"name": "large-v1", "size": "~3 GB", "lang": "Multilingual"},
    {"name": "large-v2", "size": "~3 GB", "lang": "Multilingual"},
    {"name": "large-v3", "size": "~3 GB", "lang": "Multilingual"},
]

# Whisper available models (OpenAI Whisper)
WHISPER_MODELS = [
    {"name": "tiny", "size": "~75 MB", "lang": "Multilingual"},
    {"name": "tiny.en", "size": "~75 MB", "lang": "English only"},
    {"name": "base", "size": "~150 MB", "lang": "Multilingual"},
    {"name": "base.en", "size": "~150 MB", "lang": "English only"},
    {"name": "small", "size": "~500 MB", "lang": "Multilingual"},
    {"name": "small.en", "size": "~500 MB", "lang": "English only"},
    {"name": "medium", "size": "~1.5 GB", "lang": "Multilingual"},
    {"name": "medium.en", "size": "~1.5 GB", "lang": "English only"},
    {"name": "large", "size": "~3 GB", "lang": "Multilingual"},
    {"name": "large-v1", "size": "~3 GB", "lang": "Multilingual"},
    {"name": "large-v2", "size": "~3 GB", "lang": "Multilingual"},
    {"name": "large-v3", "size": "~3 GB", "lang": "Multilingual"},
]


def fetch_models():
    try:
        response = requests.get(MODEL_LIST_URL)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching model list: {e}")
        sys.exit(1)


def list_models(models, output_dir, installed_only=False):
    print(f"{'Name':<40} {'Language':<20} {'Size':<10} {'Status':<12} {'Default'}")
    print("-" * 90)

    available_models = [m for m in models if not m.get("obsolete") == "true"]

    # Get default model path
    default_model_path = str(get_default_model_path())

    for model in available_models:
        name = model["name"]
        lang = model["lang_text"]
        size = model["size_text"]

        # Check if model exists
        target_path = os.path.join(output_dir, name)
        is_installed = os.path.exists(target_path)

        # Filter if --installed flag is set
        if installed_only and not is_installed:
            continue

        status = "Installed" if is_installed else ""

        # Check if this is the default model
        is_default = "✓" if target_path == default_model_path else ""

        print(f"{name:<40} {lang:<20} {size:<10} {status:<12} {is_default}")

    # Show footer with default model info
    if not installed_only:
        print("-" * 90)
        print(f"Default model: {os.path.basename(default_model_path)}")
        print(
            "To set a different default, create ~/.config/vosk-wrapper-1000/config.yaml"
        )

    return available_models


def delete_model(model_name, output_dir):
    target_path = os.path.join(output_dir, model_name)

    if not os.path.exists(target_path):
        print(f"Error: Model '{model_name}' not found at '{target_path}'.")
        return False

    try:
        shutil.rmtree(target_path)
        print(f"Model '{model_name}' deleted successfully from '{target_path}'.")
        return True
    except Exception as e:
        print(f"Error deleting model '{model_name}': {e}")
        return False


def download_model(model_name, output_dir, models=None):
    if models is None:
        models = fetch_models()

    model_info = next((m for m in models if m["name"] == model_name), None)

    if not model_info:
        print(f"Error: Model '{model_name}' not found.")
        return None

    url = model_info["url"]
    target_path = os.path.join(output_dir, model_name)

    if os.path.exists(target_path):
        print(f"Model '{model_name}' already exists at '{target_path}'.")
        return target_path

    os.makedirs(output_dir, exist_ok=True)

    print(f"Downloading {model_name} from {url}...")
    response = requests.get(url, stream=True)
    total_size_in_bytes = int(response.headers.get("content-length", 0))
    block_size = 1024
    progress_bar = tqdm(total=total_size_in_bytes, unit="iB", unit_scale=True)

    zip_path = os.path.join(output_dir, f"{model_name}.zip")
    with open(zip_path, "wb") as file:
        for data in response.iter_content(block_size):
            progress_bar.update(len(data))
            file.write(data)
    progress_bar.close()

    print("Extracting model...")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(output_dir)

    os.remove(zip_path)
    print(f"Model ready at '{target_path}'.")
    return target_path


def list_faster_whisper_models(output_dir, installed_only=False):
    """List available FasterWhisper models."""
    print(f"{'Name':<15} {'Language':<20} {'Size':<10} {'Status':<12} {'Downloaded'}")
    print("-" * 70)

    for model in FASTER_WHISPER_MODELS:
        name = model["name"]
        lang = model["lang"]
        size = model["size"]

        # Check if model is downloaded (FasterWhisper stores in HF cache)
        # We'll check our custom directory
        target_path = os.path.join(output_dir, name)
        is_installed = os.path.exists(target_path)

        if installed_only and not is_installed:
            continue

        status = "Downloaded" if is_installed else "Available"
        downloaded_mark = "✓" if is_installed else ""

        print(f"{name:<15} {lang:<20} {size:<10} {status:<12} {downloaded_mark}")

    print("-" * 70)
    print(f"Models will be downloaded to: {output_dir}")
    print("Note: FasterWhisper models are auto-downloaded on first use.")


def list_whisper_models(output_dir, installed_only=False):
    """List available Whisper models."""
    print(f"{'Name':<15} {'Language':<20} {'Size':<10} {'Status':<12} {'Downloaded'}")
    print("-" * 70)

    for model in WHISPER_MODELS:
        name = model["name"]
        lang = model["lang"]
        size = model["size"]

        # Check if model is downloaded
        target_path = os.path.join(output_dir, f"{name}.pt")
        is_installed = os.path.exists(target_path)

        if installed_only and not is_installed:
            continue

        status = "Downloaded" if is_installed else "Available"
        downloaded_mark = "✓" if is_installed else ""

        print(f"{name:<15} {lang:<20} {size:<10} {status:<12} {downloaded_mark}")

    print("-" * 70)
    print(f"Models will be downloaded to: {output_dir}")
    print("Note: Whisper models are auto-downloaded on first use.")


def download_faster_whisper_model(model_name, output_dir):
    """Download a FasterWhisper model."""
    try:
        from faster_whisper import WhisperModel  # type: ignore[import-untyped]
    except ImportError:
        print("Error: faster-whisper is not installed.")
        print("Install it with: uv sync --extra faster-whisper")
        return None

    model_info = next(
        (m for m in FASTER_WHISPER_MODELS if m["name"] == model_name), None
    )

    if not model_info:
        print(f"Error: Model '{model_name}' not found.")
        print("Available models:")
        for m in FASTER_WHISPER_MODELS:
            print(f"  - {m['name']}")
        return None

    target_path = os.path.join(output_dir, model_name)

    if os.path.exists(target_path):
        print(f"Model '{model_name}' already exists at '{target_path}'.")
        return target_path

    os.makedirs(output_dir, exist_ok=True)

    print(f"Downloading FasterWhisper model '{model_name}'...")
    print(
        "Note: This will download to Hugging Face cache, "
        "then link to the models directory."
    )

    try:
        # Download by instantiating the model (downloads to HF cache)
        print("Loading model (this will trigger download)...")
        WhisperModel(model_name, device="cpu", compute_type="int8")

        # Create a marker file in our models directory
        os.makedirs(target_path, exist_ok=True)
        marker_file = os.path.join(target_path, "downloaded.txt")
        with open(marker_file, "w") as f:
            f.write(f"FasterWhisper model '{model_name}' downloaded successfully.\n")
            f.write("Model is cached in Hugging Face cache directory.\n")

        print(f"Model '{model_name}' downloaded successfully!")
        print(f"Marker created at: {target_path}")
        return target_path
    except Exception as e:
        print(f"Error downloading model: {e}")
        return None


def download_whisper_model(model_name, output_dir):
    """Download a Whisper model."""
    try:
        import whisper  # type: ignore[import-untyped]
    except ImportError:
        print("Error: openai-whisper is not installed.")
        print("Install it with: uv sync --extra whisper")
        return None

    model_info = next((m for m in WHISPER_MODELS if m["name"] == model_name), None)

    if not model_info:
        print(f"Error: Model '{model_name}' not found.")
        print("Available models:")
        for m in WHISPER_MODELS:
            print(f"  - {m['name']}")
        return None

    print(f"Downloading Whisper model '{model_name}'...")
    print("Note: This will download to Whisper's cache directory.")

    try:
        # Download by loading the model
        print("Loading model (this will trigger download)...")
        whisper.load_model(model_name)

        # Create a marker in our models directory
        os.makedirs(output_dir, exist_ok=True)
        marker_file = os.path.join(output_dir, f"{model_name}.txt")
        with open(marker_file, "w") as f:
            f.write(f"Whisper model '{model_name}' downloaded successfully.\n")
            f.write("Model is cached in Whisper cache directory.\n")

        print(f"Model '{model_name}' downloaded successfully!")
        print(f"Marker created at: {marker_file}")
        return marker_file
    except Exception as e:
        print(f"Error downloading model: {e}")
        return None


def interactive_mode(output_dir):
    models = fetch_models()
    available_models = list_models(models, output_dir)

    print("\nEnter the name of the model to download (or 'q' to quit):")
    while True:
        choice = input("> ").strip()
        if choice.lower() == "q":
            break

        model = next((m for m in available_models if m["name"] == choice), None)
        if model:
            download_model(choice, output_dir, models)
            # Refresh list to show installed status
            print("\n")
            list_models(models, output_dir)
            print("\nEnter another model name or 'q' to quit:")
        else:
            print("Invalid model name. Please try again.")


def main():
    parser = argparse.ArgumentParser(
        description="Download and manage speech recognition models.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all available Vosk models (default)
  vosk-download-model-1000

  # List FasterWhisper models
  vosk-download-model-1000 --backend faster-whisper

  # List Whisper models
  vosk-download-model-1000 --backend whisper

  # Download a Vosk model
  vosk-download-model-1000 vosk-model-small-en-us-0.15

  # Download a FasterWhisper model
  vosk-download-model-1000 --backend faster-whisper base.en

  # Download a Whisper model
  vosk-download-model-1000 --backend whisper medium

  # Delete a model
  vosk-download-model-1000 --delete vosk-model-small-en-us-0.15
        """,
    )
    parser.add_argument(
        "name", nargs="?", type=str, help="Name of the model to download"
    )
    parser.add_argument(
        "--backend",
        "-b",
        type=str,
        choices=["vosk", "faster-whisper", "whisper"],
        default="vosk",
        help="Backend type (default: vosk)",
    )
    parser.add_argument(
        "--installed", action="store_true", help="List only installed models"
    )
    parser.add_argument(
        "--delete", action="store_true", help="Delete the specified model"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Directory to store models (default: backend-specific)",
    )

    args = parser.parse_args()

    # Determine output directory based on backend
    if args.output is None:
        base_dir = Path(DEFAULT_OUTPUT_DIR)
        if args.backend == "faster-whisper":
            output_dir = str(base_dir / "faster-whisper")
        elif args.backend == "whisper":
            output_dir = str(base_dir / "whisper")
        else:  # vosk
            output_dir = str(base_dir / "vosk")
    else:
        output_dir = args.output

    # Handle delete operation
    if args.delete:
        if not args.name:
            print("Error: --delete requires a model name.")
            parser.print_help()
            sys.exit(1)
        delete_model(args.name, output_dir)
    # Handle download operation
    elif args.name:
        if args.backend == "faster-whisper":
            download_faster_whisper_model(args.name, output_dir)
        elif args.backend == "whisper":
            download_whisper_model(args.name, output_dir)
        else:  # vosk
            download_model(args.name, output_dir)
    # Handle list operation (default when no name provided)
    else:
        if args.backend == "faster-whisper":
            list_faster_whisper_models(output_dir, installed_only=args.installed)
        elif args.backend == "whisper":
            list_whisper_models(output_dir, installed_only=args.installed)
        else:  # vosk
            models = fetch_models()
            list_models(models, output_dir, installed_only=args.installed)


if __name__ == "__main__":
    main()
