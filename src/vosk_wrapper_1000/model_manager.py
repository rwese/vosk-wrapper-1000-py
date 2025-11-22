"""Vosk model management utilities."""

import os
from typing import List, Tuple

from .xdg_paths import get_default_model_path, get_models_dir


class ModelManager:
    """Manages Vosk model loading and configuration."""

    def __init__(self):
        self.models_dir = get_models_dir()
        self.default_model = get_default_model_path()

    def get_model_sample_rate(self, model_path: str) -> int:
        """Extract sample rate from model's mfcc.conf file."""
        mfcc_conf = os.path.join(model_path, "conf", "mfcc.conf")
        if os.path.exists(mfcc_conf):
            try:
                with open(mfcc_conf) as f:
                    for line in f:
                        if "--sample-frequency" in line:
                            # Extract: --sample-frequency=16000
                            rate = int(line.split("=")[1].strip())
                            return rate
            except (OSError, ValueError, IndexError):
                pass
        # Default to 16000 if not found
        return 16000

    def validate_model(self, model_path: str) -> Tuple[bool, str]:
        """Validate that model exists and is accessible."""
        if not os.path.exists(model_path):
            return False, f"Model path does not exist: {model_path}"

        if not os.path.isdir(model_path):
            return False, f"Model path is not a directory: {model_path}"

        # Check for required model files
        required_files = ["am/final.mdl", "conf/mfcc.conf", "graph/HCLG.fst"]
        missing_files = []
        for file_path in required_files:
            full_path = os.path.join(model_path, file_path)
            if not os.path.exists(full_path):
                missing_files.append(file_path)

        if missing_files:
            return False, f"Model missing required files: {', '.join(missing_files)}"

        return True, "Model validation passed"

    def list_available_models(self) -> List[str]:
        """List all available models in the models directory."""
        models = []
        if os.path.exists(self.models_dir):
            for item in os.listdir(self.models_dir):
                model_path = os.path.join(self.models_dir, item)
                if os.path.isdir(model_path):
                    models.append(item)
        return models

    def get_model_info(self, model_name: str) -> dict:
        """Get detailed information about a specific model."""
        model_path = os.path.join(self.models_dir, model_name)
        info = {
            "name": model_name,
            "path": model_path,
            "exists": os.path.exists(model_path),
            "sample_rate": None,
            "size_mb": None,
        }

        if info["exists"]:
            info["sample_rate"] = self.get_model_sample_rate(model_path)
            # Calculate approximate size
            try:
                total_size = 0
                for root, _dirs, files in os.walk(model_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if os.path.exists(file_path):
                            total_size += os.path.getsize(file_path)
                info["size_mb"] = round(total_size / (1024 * 1024), 2)
            except Exception:
                pass

        return info
