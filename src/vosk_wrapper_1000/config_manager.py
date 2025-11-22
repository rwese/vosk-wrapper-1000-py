"""
Configuration management for vosk-simple.

This module provides centralized configuration management with support for
YAML configuration files and environment variable overrides.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml

from .xdg_paths import XDGPaths


@dataclass
class AudioConfig:
    """Audio configuration settings."""

    device: str = ""
    blocksize: int = 8000
    samplerate: Optional[int] = None
    channels: int = 1
    dtype: str = "int16"
    noise_reduction: bool = True


@dataclass
class ModelConfig:
    """Model configuration settings."""

    path: Optional[str] = None
    default_name: str = "vosk-model-small-en-us-0.15"
    auto_download: bool = False


@dataclass
class RecognitionConfig:
    """Recognition configuration settings."""

    words: bool = False
    partial_words: bool = False
    grammar: Optional[str] = None
    max_alternatives: int = 1


@dataclass
class HooksConfig:
    """Hook configuration settings."""

    enabled: bool = True
    directory: Optional[str] = None
    timeout: int = 30


@dataclass
class LoggingConfig:
    """Logging configuration settings."""

    level: str = "INFO"
    file: Optional[str] = None
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@dataclass
class PerformanceConfig:
    """Performance configuration settings."""

    queue_size: int = 100
    sleep_time: float = 0.1
    threaded: bool = True


@dataclass
class ServiceConfig:
    """Service configuration settings."""

    instance_name: str = "default"
    pid_directory: Optional[str] = None
    shutdown_timeout: int = 10


@dataclass
class Config:
    """Main configuration class containing all settings."""

    audio: AudioConfig = field(default_factory=AudioConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    recognition: RecognitionConfig = field(default_factory=RecognitionConfig)
    hooks: HooksConfig = field(default_factory=HooksConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    service: ServiceConfig = field(default_factory=ServiceConfig)


class ConfigManager:
    """Manages configuration loading and access."""

    def __init__(self, config_file: Optional[Union[str, Path]] = None):
        """Initialize configuration manager.

        Args:
            config_file: Path to configuration file. If None, uses default locations.
        """
        self.xdg_paths = XDGPaths()
        self.config_file = self._resolve_config_file(config_file)
        self._config: Optional[Config] = None

    def _resolve_config_file(
        self, config_file: Optional[Union[str, Path]]
    ) -> Optional[Path]:
        """Resolve configuration file path.

        Args:
            config_file: Explicit config file path or None

        Returns:
            Resolved path to config file or None if not found
        """
        if config_file:
            path = Path(config_file)
            if path.exists():
                return path
            return None

        # Check XDG config directory
        xdg_config = self.xdg_paths.get_config_dir() / "vosk-simple" / "config.yaml"
        if xdg_config.exists():
            return xdg_config

        # Check local config directory
        local_config = Path("config/default.yaml")
        if local_config.exists():
            return local_config

        # Check project root
        root_config = Path("config.yaml")
        if root_config.exists():
            return root_config

        return None

    def load_config(self) -> Config:
        """Load configuration from file and environment variables.

        Returns:
            Loaded configuration object
        """
        if self._config is None:
            self._config = self._load_config()
        return self._config

    def _load_config(self) -> Config:
        """Internal method to load configuration."""
        config_data = {}

        # Load from file if available
        if self.config_file:
            try:
                with open(self.config_file) as f:
                    config_data = yaml.safe_load(f) or {}
            except (OSError, yaml.YAMLError) as e:
                print(f"Warning: Failed to load config file {self.config_file}: {e}")

        # Create config object
        config = self._create_config_from_dict(config_data)

        # Apply environment variable overrides
        self._apply_env_overrides(config)

        return config

    def _create_config_from_dict(self, data: Dict[str, Any]) -> Config:
        """Create Config object from dictionary data."""
        return Config(
            audio=AudioConfig(**data.get("audio", {})),
            model=ModelConfig(**data.get("model", {})),
            recognition=RecognitionConfig(**data.get("recognition", {})),
            hooks=HooksConfig(**data.get("hooks", {})),
            logging=LoggingConfig(**data.get("logging", {})),
            performance=PerformanceConfig(**data.get("performance", {})),
            service=ServiceConfig(**data.get("service", {})),
        )

    def _apply_env_overrides(self, config: Config) -> None:
        """Apply environment variable overrides to configuration."""
        # Audio overrides
        if os.getenv("VOSK_AUDIO_DEVICE"):
            config.audio.device = os.getenv("VOSK_AUDIO_DEVICE")
        if os.getenv("VOSK_AUDIO_BLOCKSIZE"):
            config.audio.blocksize = int(os.getenv("VOSK_AUDIO_BLOCKSIZE"))
        if os.getenv("VOSK_AUDIO_SAMPLERATE"):
            config.audio.samplerate = int(os.getenv("VOSK_AUDIO_SAMPLERATE"))

        # Model overrides
        if os.getenv("VOSK_MODEL_PATH"):
            config.model.path = os.getenv("VOSK_MODEL_PATH")
        if os.getenv("VOSK_MODEL_NAME"):
            config.model.default_name = os.getenv("VOSK_MODEL_NAME")

        # Recognition overrides
        if os.getenv("VOSK_WORDS"):
            config.recognition.words = os.getenv("VOSK_WORDS").lower() in (
                "true",
                "1",
                "yes",
            )
        if os.getenv("VOSK_PARTIAL_WORDS"):
            config.recognition.partial_words = os.getenv(
                "VOSK_PARTIAL_WORDS"
            ).lower() in ("true", "1", "yes")
        if os.getenv("VOSK_GRAMMAR"):
            config.recognition.grammar = os.getenv("VOSK_GRAMMAR")

        # Logging overrides
        if os.getenv("VOSK_LOG_LEVEL"):
            config.logging.level = os.getenv("VOSK_LOG_LEVEL")
        if os.getenv("VOSK_LOG_FILE"):
            config.logging.file = os.getenv("VOSK_LOG_FILE")

        # Service overrides
        if os.getenv("VOSK_INSTANCE_NAME"):
            config.service.instance_name = os.getenv("VOSK_INSTANCE_NAME")

    def save_config(
        self, config: Config, file_path: Optional[Union[str, Path]] = None
    ) -> None:
        """Save configuration to file.

        Args:
            config: Configuration object to save
            file_path: Path to save to. If None, uses current config file.
        """
        if file_path is None:
            file_path = self.config_file

        if file_path is None:
            raise ValueError("No config file path specified")

        config_dict = {
            "audio": {
                "device": config.audio.device,
                "blocksize": config.audio.blocksize,
                "samplerate": config.audio.samplerate,
                "channels": config.audio.channels,
                "dtype": config.audio.dtype,
                "noise_reduction": config.audio.noise_reduction,
            },
            "model": {
                "path": config.model.path,
                "default_name": config.model.default_name,
                "auto_download": config.model.auto_download,
            },
            "recognition": {
                "words": config.recognition.words,
                "partial_words": config.recognition.partial_words,
                "grammar": config.recognition.grammar,
                "max_alternatives": config.recognition.max_alternatives,
            },
            "hooks": {
                "enabled": config.hooks.enabled,
                "directory": config.hooks.directory,
                "timeout": config.hooks.timeout,
            },
            "logging": {
                "level": config.logging.level,
                "file": config.logging.file,
                "format": config.logging.format,
            },
            "performance": {
                "queue_size": config.performance.queue_size,
                "sleep_time": config.performance.sleep_time,
                "threaded": config.performance.threaded,
            },
            "service": {
                "instance_name": config.service.instance_name,
                "pid_directory": config.service.pid_directory,
                "shutdown_timeout": config.service.shutdown_timeout,
            },
        }

        # Ensure directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)

    def get_config_file_path(self) -> Optional[Path]:
        """Get the path to the current configuration file."""
        return self.config_file


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_file: Optional[Union[str, Path]] = None) -> ConfigManager:
    """Get the global configuration manager instance.

    Args:
        config_file: Path to configuration file (only used on first call)

    Returns:
        Configuration manager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_file)
    return _config_manager


def load_config(config_file: Optional[Union[str, Path]] = None) -> Config:
    """Load configuration using the global config manager.

    Args:
        config_file: Path to configuration file (only used on first call)

    Returns:
        Loaded configuration object
    """
    return get_config_manager(config_file).load_config()
