"""XDG Base Directory specification helper for vosk-wrapper-1000."""
import os
from pathlib import Path

APP_NAME = "vosk-wrapper-1000"

def get_xdg_config_home():
    """Get XDG_CONFIG_HOME directory (default: ~/.config)."""
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

def get_xdg_data_home():
    """Get XDG_DATA_HOME directory (default: ~/.local/share)."""
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

def get_xdg_cache_home():
    """Get XDG_CACHE_HOME directory (default: ~/.cache)."""
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))

def get_hooks_dir():
    """Get the hooks directory path."""
    hooks_dir = get_xdg_config_home() / APP_NAME / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    return hooks_dir

def get_models_dir():
    """Get the models directory path."""
    models_dir = get_xdg_data_home() / APP_NAME / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    return models_dir

def get_default_model_path():
    """Get the default model path (first model found in models directory)."""
    models_dir = get_models_dir()

    # Check if there's a 'model' symlink or directory (for backwards compatibility)
    if models_dir.parent.parent.parent.exists():
        legacy_model = models_dir.parent.parent.parent / "model"
        if legacy_model.exists():
            return legacy_model

    # Look for any model in the XDG models directory
    if models_dir.exists():
        for item in models_dir.iterdir():
            if item.is_dir() and item.name.startswith("vosk-model"):
                return item

    # Return the expected default path (may not exist yet)
    return models_dir / "model"
