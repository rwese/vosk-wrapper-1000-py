#!/bin/bash

# Ensure we are in the script's directory
cd "$(dirname "$0")"

VENV_DIR="venv"
REQUIREMENTS="requirements.txt"
MODELS_DIR="models"
MODEL_NAME="small-en" # Default model

# Parse arguments for model name
# We extract --model-name if present, otherwise pass everything to main.py
ARGS=()
while [[ $# -gt 0 ]]; do
  case $1 in
    --model-name)
      MODEL_NAME="$2"
      shift # past argument
      shift # past value
      ;;
    *)
      ARGS+=("$1")
      shift # past argument
      ;;
  esac
done

# Check if venv exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    
    # Install requirements
    if [ -f "$REQUIREMENTS" ]; then
        echo "Installing requirements..."
        "$VENV_DIR/bin/pip" install -r "$REQUIREMENTS"
    fi
fi

# Ensure model exists
# We run download_model.py to check/download. It returns the path if we capture stdout, 
# but it prints progress bars etc. 
# Simpler: just run it, it handles "already exists" logic.
"$VENV_DIR/bin/python" download_model.py --name "$MODEL_NAME" --output "$MODELS_DIR"

# Determine the model path. 
# Since download_model.py knows the mapping, we need to know where it put it.
# We can use a small python snippet or just rely on the known structure if we want to be robust.
# Let's ask download_model.py to print the path? 
# Or we can just let main.py find it if we pass the directory? 
# Vosk needs the specific model folder.
# Let's use python to get the path from the map.
MODEL_PATH=$("$VENV_DIR/bin/python" -c "import download_model; print(download_model.download_model('$MODEL_NAME', '$MODELS_DIR'))" | tail -n 1)

# Run the application
exec "$VENV_DIR/bin/python" main.py --model "$MODEL_PATH" "${ARGS[@]}"
