"""XDG Base Directory specification helper for vosk-wrapper-1000."""

import os
from pathlib import Path

APP_NAME = "vosk-wrapper-1000"


def _load_user_config():
    """Load user configuration if it exists.

    Returns:
        Dict with config data or empty dict if no config found
    """
    try:
        import yaml

        config_path = (
            Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
            / APP_NAME
            / "config.yaml"
        )
        if config_path.exists():
            with open(config_path) as f:
                return yaml.safe_load(f) or {}
    except Exception:
        pass
    return {}


class XDGPaths:
    """XDG paths manager class."""

    def __init__(self, app_name: str = APP_NAME):
        """Initialize XDG paths manager.

        Args:
            app_name: Application name for path construction
        """
        self.app_name = app_name

    def get_config_dir(self, subpath: str = "") -> Path:
        """Get XDG config directory.

        Args:
            subpath: Optional subpath within config directory

        Returns:
            Path to config directory
        """
        base_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        if subpath:
            config_dir = base_dir / self.app_name / subpath
        else:
            config_dir = base_dir / self.app_name
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    def get_data_dir(self, subpath: str = "") -> Path:
        """Get XDG data directory.

        Args:
            subpath: Optional subpath within data directory

        Returns:
            Path to data directory
        """
        base_dir = Path(
            os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
        )
        if subpath:
            data_dir = base_dir / self.app_name / subpath
        else:
            data_dir = base_dir / self.app_name
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    def get_cache_dir(self, subpath: str = "") -> Path:
        """Get XDG cache directory.

        Args:
            subpath: Optional subpath within cache directory

        Returns:
            Path to cache directory
        """
        base_dir = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
        if subpath:
            cache_dir = base_dir / self.app_name / subpath
        else:
            cache_dir = base_dir / self.app_name
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def get_model_dir(self) -> Path:
        """Get models directory path."""
        return self.get_data_dir("models")

    def get_hooks_dir(self) -> Path:
        """Get hooks directory path."""
        return self.get_config_dir("hooks")


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
    """Get the default model path.

    Priority:
    1. User config file (~/.config/vosk-wrapper-1000/config.yaml)
    2. First model found in models directory
    3. Default fallback path
    """
    models_dir = get_models_dir()

    # Check user config file first
    user_config = _load_user_config()
    if user_config.get("model", {}).get("path"):
        config_model_path = Path(user_config["model"]["path"])
        if config_model_path.exists():
            return config_model_path

    # Look for any model in the XDG models directory
    if models_dir.exists():
        for item in models_dir.iterdir():
            if item.is_dir() and item.name.startswith("vosk-model"):
                return item

    # Return the expected default path (may not exist yet)
    return models_dir / "model"
