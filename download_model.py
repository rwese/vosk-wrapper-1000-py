import argparse
import os
import sys
import requests
import zipfile
from tqdm import tqdm
import json

MODEL_LIST_URL = "https://alphacephei.com/vosk/models/model-list.json"
DEFAULT_OUTPUT_DIR = "models"

def fetch_models():
    try:
        response = requests.get(MODEL_LIST_URL)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching model list: {e}")
        sys.exit(1)

def list_models(models, output_dir):
    print(f"{'Name':<40} {'Language':<20} {'Size':<10} {'Status'}")
    print("-" * 80)
    
    available_models = [m for m in models if not m.get('obsolete') == 'true']
    
    for model in available_models:
        name = model['name']
        lang = model['lang_text']
        size = model['size_text']
        
        # Check if model exists
        target_path = os.path.join(output_dir, name)
        status = "Installed" if os.path.exists(target_path) else ""
        
        print(f"{name:<40} {lang:<20} {size:<10} {status}")
    return available_models

def download_model(model_name, output_dir, models=None):
    if models is None:
        models = fetch_models()
    
    model_info = next((m for m in models if m['name'] == model_name), None)
    
    if not model_info:
        print(f"Error: Model '{model_name}' not found.")
        return None

    url = model_info['url']
    target_path = os.path.join(output_dir, model_name)

    if os.path.exists(target_path):
        print(f"Model '{model_name}' already exists at '{target_path}'.")
        return target_path

    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Downloading {model_name} from {url}...")
    response = requests.get(url, stream=True)
    total_size_in_bytes = int(response.headers.get('content-length', 0))
    block_size = 1024
    progress_bar = tqdm(total=total_size_in_bytes, unit='iB', unit_scale=True)
    
    zip_path = os.path.join(output_dir, f"{model_name}.zip")
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

def interactive_mode(output_dir):
    models = fetch_models()
    available_models = list_models(models, output_dir)
    
    print("\nEnter the name of the model to download (or 'q' to quit):")
    while True:
        choice = input("> ").strip()
        if choice.lower() == 'q':
            break
        
        model = next((m for m in available_models if m['name'] == choice), None)
        if model:
            download_model(choice, output_dir, models)
            # Refresh list to show installed status
            print("\n")
            list_models(models, output_dir)
            print("\nEnter another model name or 'q' to quit:")
        else:
            print("Invalid model name. Please try again.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Vosk models.")
    parser.add_argument("--list", action="store_true", help="List available models")
    parser.add_argument("--name", type=str, help="Name of the model to download")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT_DIR, help="Directory to store models")
    
    args = parser.parse_args()

    if args.list:
        models = fetch_models()
        list_models(models, args.output)
    elif args.name:
        download_model(args.name, args.output)
    else:
        interactive_mode(args.output)
