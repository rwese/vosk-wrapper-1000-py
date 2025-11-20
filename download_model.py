import argparse
import os
import sys
import requests
import zipfile
from tqdm import tqdm

# Define available models
MODELS = {
    "small-en": "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
    "en": "https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip",
    "en-large": "https://alphacephei.com/vosk/models/vosk-model-en-us-0.42-gigaspeech.zip",
    "small-cn": "https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip",
    "cn": "https://alphacephei.com/vosk/models/vosk-model-cn-0.22.zip",
    "small-ru": "https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip",
    "ru": "https://alphacephei.com/vosk/models/vosk-model-ru-0.42.zip",
    "small-fr": "https://alphacephei.com/vosk/models/vosk-model-small-fr-0.22.zip",
    "fr": "https://alphacephei.com/vosk/models/vosk-model-fr-0.22.zip",
    "small-de": "https://alphacephei.com/vosk/models/vosk-model-small-de-0.15.zip",
    "de": "https://alphacephei.com/vosk/models/vosk-model-de-0.21.zip",
    "small-es": "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip",
    "es": "https://alphacephei.com/vosk/models/vosk-model-es-0.42.zip",
    "small-pt": "https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip",
    "small-tr": "https://alphacephei.com/vosk/models/vosk-model-small-tr-0.3.zip",
    "small-vn": "https://alphacephei.com/vosk/models/vosk-model-small-vn-0.4.zip",
    "small-it": "https://alphacephei.com/vosk/models/vosk-model-small-it-0.22.zip",
    "small-nl": "https://alphacephei.com/vosk/models/vosk-model-small-nl-0.22.zip",
}

DEFAULT_MODEL = "small-en"
DEFAULT_OUTPUT_DIR = "models"

def list_models():
    print("Available models:")
    for name, url in MODELS.items():
        print(f"  {name:<12} : {url}")

def download_model(model_name, output_dir):
    if model_name not in MODELS:
        print(f"Error: Model '{model_name}' not found. Use --list to see available models.")
        sys.exit(1)

    url = MODELS[model_name]
    model_zip_name = url.split("/")[-1]
    model_folder_name = model_zip_name.replace(".zip", "")
    target_path = os.path.join(output_dir, model_folder_name)

    if os.path.exists(target_path):
        print(f"Model '{model_name}' already exists at '{target_path}'.")
        return target_path

    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Downloading {model_name} from {url}...")
    response = requests.get(url, stream=True)
    total_size_in_bytes = int(response.headers.get('content-length', 0))
    block_size = 1024
    progress_bar = tqdm(total=total_size_in_bytes, unit='iB', unit_scale=True)
    
    zip_path = os.path.join(output_dir, model_zip_name)
    with open(zip_path, 'wb') as file:
        for data in response.iter_content(block_size):
            progress_bar.update(len(data))
            file.write(data)
    progress_bar.close()

    print("Extracting model...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(output_dir)
    
    os.remove(zip_path)
    print(f"Model ready at '{target_path}'.")
    return target_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Vosk models.")
    parser.add_argument("--list", action="store_true", help="List available models")
    parser.add_argument("--name", type=str, default=DEFAULT_MODEL, help="Name of the model to download")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT_DIR, help="Directory to store models")
    
    args = parser.parse_args()

    if args.list:
        list_models()
    else:
        download_model(args.name, args.output)
