"""
Configuration management for vosk-simple.

This module provides centralized configuration management with support for
YAML configuration files and environment variable overrides.
"""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from vosk_core.xdg_paths import XDGPaths


@dataclass
class AudioConfig:
    """Audio configuration settings."""

    device: str = ""
    default_device: str = ""  # Default device name/ID, empty means system default
    blocksize: int = 8000
    samplerate: int | None = None
    channels: int = 1
    dtype: str = "int16"
    noise_reduction: bool = True
    # Audio processing settings
    noise_reduction_enabled: bool = True
    noise_reduction_level: float = 0.05
    stationary_noise: bool = False
    silence_threshold: float = 50.0
    normalize_audio: bool = False
    normalization_target_level: float = 0.3
    vad_hysteresis_chunks: int = 10
    pre_roll_duration: float = 0.5
    noise_reduction_min_rms_ratio: float = 0.5
    passthrough_mode: bool = (
        False  # If True, bypass VAD and process all audio continuously
    )


@dataclass
class ModelConfig:
    """Model configuration settings."""

    path: str | None = None
    default_name: str = "vosk-model-small-en-us-0.15"
    auto_download: bool = False


@dataclass
class BackendConfig:
    """Recognition backend configuration."""

    type: str = "vosk"  # vosk, faster-whisper, whisper


@dataclass
class RecognitionConfig:
    """Recognition configuration settings (legacy, maps to VoskOptions)."""

    words: bool = False
    partial_words: bool = False
    grammar: str | None = None
    max_alternatives: int = 1


@dataclass
class VoskOptions:
    """Vosk-specific recognition options."""

    words: bool = False
    partial_words: bool = False
    grammar: str | None = None
    max_alternatives: int = 1


@dataclass
class FasterWhisperOptions:
    """FasterWhisper-specific recognition options."""

    device: str = "cpu"  # cpu, cuda, auto
    compute_type: str = "int8"  # int8, int16, float16, float32
    beam_size: int = 5
    language: str | None = None  # auto-detect if None
    vad_filter: bool = True
    best_of: int = 5  # Number of candidates for beam search
    patience: float = 1.0  # Beam search patience
    length_penalty: float = 1.0  # Length penalty
    repetition_penalty: float = 1.0  # Repetition penalty
    no_repeat_ngram_size: int = 0  # Prevent n-gram repetition


@dataclass
class WhisperOptions:
    """OpenAI Whisper-specific recognition options."""

    device: str = "cpu"  # cpu, cuda
    language: str | None = None  # auto-detect if None
    temperature: float = 0.0  # Sampling temperature
    fp16: bool = False  # Use FP16 if GPU available
    best_of: int = 5  # Number of candidates for beam search
    beam_size: int = 5  # Beam size for beam search
    patience: float = 1.0  # Beam search patience
    length_penalty: float = 1.0  # Length penalty
    suppress_tokens: str = "-1"  # Tokens to suppress
    initial_prompt: str | None = None  # Initial prompt for context


@dataclass
class HooksConfig:
    """Hook configuration settings."""

    enabled: bool = True
    directory: str | None = None
    timeout: int = 30


@dataclass
class LoggingConfig:
    """Logging configuration settings."""

    level: str = "INFO"
    file: str | None = None
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
    pid_directory: str | None = None
    shutdown_timeout: int = 10


@dataclass
class IPCConfig:
    """IPC configuration settings."""

    enabled: bool = True
    socket_path: str = "/tmp/vosk-wrapper-{instance_name}.sock"
    send_partials: bool = True
    timeout: float = 5.0


@dataclass
class WebRTCConfig:
    """WebRTC configuration settings."""

    enabled: bool = False
    port: int = 8080
    host: str = "0.0.0.0"
    stun_servers: list[str] = field(
        default_factory=lambda: ["stun:stun.l.google.com:19302"]
    )
    turn_servers: list[str] = field(default_factory=list)
    max_connections: int = 5
    audio_format: str = "opus"
    sample_rate: int = 48000
    channels: int = 1


@dataclass
class Config:
    """Main configuration class containing all settings."""

    audio: AudioConfig = field(default_factory=AudioConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    backend: BackendConfig = field(default_factory=BackendConfig)
    recognition: RecognitionConfig = field(default_factory=RecognitionConfig)
    vosk_options: VoskOptions = field(default_factory=VoskOptions)
    faster_whisper_options: FasterWhisperOptions = field(
        default_factory=FasterWhisperOptions
    )
    whisper_options: WhisperOptions = field(default_factory=WhisperOptions)
    hooks: HooksConfig = field(default_factory=HooksConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    service: ServiceConfig = field(default_factory=ServiceConfig)
    ipc: IPCConfig = field(default_factory=IPCConfig)
    webrtc: WebRTCConfig = field(default_factory=WebRTCConfig)


class ConfigManager:
    """Manages configuration loading and access."""

    def __init__(self, config_file: str | Path | None = None):
        """Initialize configuration manager.

        Args:
            config_file: Path to configuration file. If None, uses default locations.
        """
        self.xdg_paths = XDGPaths()
        self.config_file = self._resolve_config_file(config_file)
        self._config: Config | None = None

    def _resolve_config_file(self, config_file: str | Path | None) -> Path | None:
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
        xdg_config = self.xdg_paths.get_config_dir() / "config.yaml"
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
            print(f"✅ Configuration loaded from: {self.config_file}", file=sys.stderr)
        return self._config

    def reload_config(self) -> Config:
        """Force reload configuration from file and environment variables.

        Returns:
            Freshly loaded configuration object
        """
        self._config = self._load_config()
        print(f"✅ Configuration reloaded from: {self.config_file}", file=sys.stderr)
        return self._config

    def _load_config(self) -> Config:
        """Internal method to load configuration."""
        config_data: dict[str, Any] = {}

        # Load from file if available
        if self.config_file:
            try:
                with open(self.config_file) as f:
                    config_data = yaml.safe_load(f) or {}
                    print(
                        f"✅ Configuration loaded from: {self.config_file}",
                        file=sys.stderr,
                    )
            except (OSError, yaml.YAMLError) as e:
                print(f"Warning: Failed to load config file {self.config_file}: {e}")

        # Create config object
        config = self._create_config_from_dict(config_data)

        # Apply environment variable overrides
        self._apply_env_overrides(config)

        return config

    def _create_config_from_dict(self, data: dict[str, Any]) -> Config:
        """Create Config object from dictionary data."""
        # For backward compatibility: if vosk_options not specified,
        # use recognition config values
        vosk_opts = data.get("vosk_options", data.get("recognition", {}))

        return Config(
            audio=AudioConfig(**data.get("audio", {})),
            model=ModelConfig(**data.get("model", {})),
            backend=BackendConfig(**data.get("backend", {})),
            recognition=RecognitionConfig(**data.get("recognition", {})),
            vosk_options=VoskOptions(**vosk_opts),
            faster_whisper_options=FasterWhisperOptions(
                **data.get("faster_whisper_options", {})
            ),
            whisper_options=WhisperOptions(**data.get("whisper_options", {})),
            hooks=HooksConfig(**data.get("hooks", {})),
            logging=LoggingConfig(**data.get("logging", {})),
            performance=PerformanceConfig(**data.get("performance", {})),
            service=ServiceConfig(**data.get("service", {})),
            ipc=IPCConfig(**data.get("ipc", {})),
            webrtc=WebRTCConfig(**data.get("webrtc", {})),
        )

    def _apply_env_overrides(self, config: Config) -> None:
        """Apply environment variable overrides to configuration."""
        # Audio overrides
        if (device := os.getenv("VOSK_AUDIO_DEVICE")) is not None:
            config.audio.device = device
            print(f"🔧 Environment override: VOSK_AUDIO_DEVICE={device}")
        if (blocksize := os.getenv("VOSK_AUDIO_BLOCKSIZE")) is not None:
            config.audio.blocksize = int(blocksize)
            print(f"🔧 Environment override: VOSK_AUDIO_BLOCKSIZE={blocksize}")
        if (samplerate := os.getenv("VOSK_AUDIO_SAMPLERATE")) is not None:
            config.audio.samplerate = int(samplerate)
            print(f"🔧 Environment override: VOSK_AUDIO_SAMPLERATE={samplerate}")

        # Model overrides
        if (model_path := os.getenv("VOSK_MODEL_PATH")) is not None:
            config.model.path = model_path
            print(f"🔧 Environment override: VOSK_MODEL_PATH={model_path}")
        if (model_name := os.getenv("VOSK_MODEL_NAME")) is not None:
            config.model.default_name = model_name
            print(f"🔧 Environment override: VOSK_MODEL_NAME={model_name}")

        # Backend overrides
        if (backend_type := os.getenv("VOSK_BACKEND")) is not None:
            config.backend.type = backend_type
            print(f"🔧 Environment override: VOSK_BACKEND={backend_type}")

        # Recognition overrides
        if (words := os.getenv("VOSK_WORDS")) is not None:
            config.recognition.words = words.lower() in (
                "true",
                "1",
                "yes",
            )
        if (partial_words := os.getenv("VOSK_PARTIAL_WORDS")) is not None:
            config.recognition.partial_words = partial_words.lower() in (
                "true",
                "1",
                "yes",
            )
        if (grammar := os.getenv("VOSK_GRAMMAR")) is not None:
            config.recognition.grammar = grammar

        # Logging overrides
        if (log_level := os.getenv("VOSK_LOG_LEVEL")) is not None:
            config.logging.level = log_level
        if (log_file := os.getenv("VOSK_LOG_FILE")) is not None:
            config.logging.file = log_file

        # Service overrides
        if (instance_name := os.getenv("VOSK_INSTANCE_NAME")) is not None:
            config.service.instance_name = instance_name

        # IPC overrides
        if (ipc_enabled := os.getenv("VOSK_IPC_ENABLED")) is not None:
            config.ipc.enabled = ipc_enabled.lower() in (
                "true",
                "1",
                "yes",
            )
        if (socket_path := os.getenv("VOSK_IPC_SOCKET_PATH")) is not None:
            config.ipc.socket_path = socket_path

        # WebRTC overrides
        if (webrtc_enabled := os.getenv("VOSK_WEBRTC_ENABLED")) is not None:
            config.webrtc.enabled = webrtc_enabled.lower() in (
                "true",
                "1",
                "yes",
            )
        if (webrtc_port := os.getenv("VOSK_WEBRTC_PORT")) is not None:
            config.webrtc.port = int(webrtc_port)
        if (webrtc_host := os.getenv("VOSK_WEBRTC_HOST")) is not None:
            config.webrtc.host = webrtc_host

    def save_config(self, config: Config, file_path: str | Path | None = None) -> None:
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
                "default_device": config.audio.default_device,
                "blocksize": config.audio.blocksize,
                "samplerate": config.audio.samplerate,
                "channels": config.audio.channels,
                "dtype": config.audio.dtype,
                "noise_reduction": config.audio.noise_reduction,
                "noise_reduction_enabled": config.audio.noise_reduction_enabled,
                "noise_reduction_level": config.audio.noise_reduction_level,
                "stationary_noise": config.audio.stationary_noise,
                "silence_threshold": config.audio.silence_threshold,
                "normalize_audio": config.audio.normalize_audio,
                "normalization_target_level": config.audio.normalization_target_level,
                "vad_hysteresis_chunks": config.audio.vad_hysteresis_chunks,
                "pre_roll_duration": config.audio.pre_roll_duration,
                "noise_reduction_min_rms_ratio": config.audio.noise_reduction_min_rms_ratio,
                "passthrough_mode": config.audio.passthrough_mode,
            },
            "model": {
                "path": config.model.path,
                "default_name": config.model.default_name,
                "auto_download": config.model.auto_download,
            },
            "backend": {
                "type": config.backend.type,
            },
            "recognition": {
                "words": config.recognition.words,
                "partial_words": config.recognition.partial_words,
                "grammar": config.recognition.grammar,
                "max_alternatives": config.recognition.max_alternatives,
            },
            "vosk_options": {
                "words": config.vosk_options.words,
                "partial_words": config.vosk_options.partial_words,
                "grammar": config.vosk_options.grammar,
                "max_alternatives": config.vosk_options.max_alternatives,
            },
            "faster_whisper_options": {
                "device": config.faster_whisper_options.device,
                "compute_type": config.faster_whisper_options.compute_type,
                "beam_size": config.faster_whisper_options.beam_size,
                "language": config.faster_whisper_options.language,
                "vad_filter": config.faster_whisper_options.vad_filter,
                "best_of": config.faster_whisper_options.best_of,
                "patience": config.faster_whisper_options.patience,
                "length_penalty": config.faster_whisper_options.length_penalty,
                "repetition_penalty": config.faster_whisper_options.repetition_penalty,
                "no_repeat_ngram_size": config.faster_whisper_options.no_repeat_ngram_size,
            },
            "whisper_options": {
                "device": config.whisper_options.device,
                "language": config.whisper_options.language,
                "temperature": config.whisper_options.temperature,
                "fp16": config.whisper_options.fp16,
                "best_of": config.whisper_options.best_of,
                "beam_size": config.whisper_options.beam_size,
                "patience": config.whisper_options.patience,
                "length_penalty": config.whisper_options.length_penalty,
                "suppress_tokens": config.whisper_options.suppress_tokens,
                "initial_prompt": config.whisper_options.initial_prompt,
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
            "ipc": {
                "enabled": config.ipc.enabled,
                "socket_path": config.ipc.socket_path,
                "send_partials": config.ipc.send_partials,
                "timeout": config.ipc.timeout,
            },
            "webrtc": {
                "enabled": config.webrtc.enabled,
                "port": config.webrtc.port,
                "host": config.webrtc.host,
                "stun_servers": config.webrtc.stun_servers,
                "turn_servers": config.webrtc.turn_servers,
                "max_connections": config.webrtc.max_connections,
                "audio_format": config.webrtc.audio_format,
                "sample_rate": config.webrtc.sample_rate,
                "channels": config.webrtc.channels,
            },
        }

        # Ensure directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)

    def get_config_file_path(self) -> Path | None:
        """Get the path to the current configuration file."""
        return self.config_file


# Global configuration manager instance
_config_manager: ConfigManager | None = None


def get_config_manager(config_file: str | Path | None = None) -> ConfigManager:
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


def load_config(config_file: str | Path | None = None) -> Config:
    """Load configuration using the global config manager.

    Args:
        config_file: Path to configuration file (only used on first call)

    Returns:
        Loaded configuration object
    """
    return get_config_manager(config_file).load_config()
