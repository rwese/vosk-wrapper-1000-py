# Multi-Backend Recognition System Implementation Plan

## Overview
Refactor vosk-wrapper-1000 to support multiple speech recognition backends: Vosk, FasterWhisper, and OpenAI Whisper. This will allow users to choose the best engine for their needs (offline vs online, speed vs accuracy, etc.).

## User Requirements
- **Backends**: Support Vosk (existing), FasterWhisper, and OpenAI Whisper
- **Selection Method**: Config file + CLI argument override
- **Backend Features**: Backend-specific configuration sections for specialized options
- **Model Management**: Separate model directories per backend

## Architecture Design

### 1. Abstract Recognition Backend Interface

Create `src/vosk_core/recognition_backend.py` following the existing `AudioBackend` pattern:

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class RecognitionResult:
    """Standardized recognition result across all backends."""
    text: str
    is_partial: bool
    confidence: float
    words: Optional[list] = None  # Word-level timestamps if available
    alternatives: Optional[list] = None  # Alternative transcriptions

class RecognitionBackend(ABC):
    """Abstract base class for speech recognition backends."""

    @abstractmethod
    def __init__(self, model_path: str, sample_rate: int, **options):
        """Initialize the recognition backend."""
        pass

    @abstractmethod
    def accept_waveform(self, data: bytes) -> bool:
        """
        Process audio data.
        Returns True if final result is ready, False for partial.
        """
        pass

    @abstractmethod
    def get_result(self) -> RecognitionResult:
        """Get final recognition result."""
        pass

    @abstractmethod
    def get_partial_result(self) -> RecognitionResult:
        """Get partial recognition result."""
        pass

    @abstractmethod
    def get_final_result(self) -> RecognitionResult:
        """Get final result and flush any pending audio."""
        pass

    @abstractmethod
    def reset(self):
        """Reset recognizer state for next utterance."""
        pass

    @abstractmethod
    def set_grammar(self, grammar: Optional[str]):
        """Set grammar/constraints if supported."""
        pass

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return backend identifier (vosk, faster-whisper, whisper)."""
        pass
```

### 2. Backend Implementations

#### VoskBackend (`src/vosk_core/backends/vosk_backend.py`)
Wraps existing Vosk implementation:
- Convert Vosk JSON results to `RecognitionResult`
- Maintain existing features: grammar, word timestamps, alternatives
- Handle SetWords(), SetPartialWords(), SetMaxAlternatives()

#### FasterWhisperBackend (`src/vosk_core/backends/faster_whisper_backend.py`)
Uses faster-whisper library:
- Buffer audio chunks until speech end (VAD-based)
- Transcribe buffered audio in one shot
- Support: language hints, beam size, GPU device, compute type
- Return partial results as empty (or implement streaming if supported)

#### WhisperBackend (`src/vosk_core/backends/whisper_backend.py`)
Uses OpenAI whisper library:
- Similar buffering approach as FasterWhisper
- Support: language, temperature, model size
- Slower but more accurate
- May use GPU if available

### 3. Backend Factory

Create `src/vosk_core/backend_factory.py`:

```python
from typing import Dict, Type
from .recognition_backend import RecognitionBackend
from .backends.vosk_backend import VoskBackend
from .backends.faster_whisper_backend import FasterWhisperBackend
from .backends.whisper_backend import WhisperBackend

BACKEND_REGISTRY: Dict[str, Type[RecognitionBackend]] = {
    "vosk": VoskBackend,
    "faster-whisper": FasterWhisperBackend,
    "whisper": WhisperBackend,
}

def create_backend(
    backend_type: str,
    model_path: str,
    sample_rate: int,
    **options
) -> RecognitionBackend:
    """Create a recognition backend instance."""
    if backend_type not in BACKEND_REGISTRY:
        raise ValueError(f"Unknown backend: {backend_type}")

    backend_class = BACKEND_REGISTRY[backend_type]
    return backend_class(model_path, sample_rate, **options)

def list_available_backends() -> list[str]:
    """List all registered backends."""
    return list(BACKEND_REGISTRY.keys())
```

### 4. Configuration Updates

#### Add to `config_manager.py`:

```python
@dataclass
class BackendConfig:
    """Recognition backend configuration."""
    type: str = "vosk"  # vosk, faster-whisper, whisper

@dataclass
class VoskOptions:
    """Vosk-specific options."""
    words: bool = False
    partial_words: bool = False
    grammar: Optional[str] = None
    max_alternatives: int = 1

@dataclass
class FasterWhisperOptions:
    """FasterWhisper-specific options."""
    device: str = "cpu"  # cpu, cuda, auto
    compute_type: str = "int8"  # int8, int16, float16, float32
    beam_size: int = 5
    language: Optional[str] = None  # auto-detect if None
    vad_filter: bool = True

@dataclass
class WhisperOptions:
    """OpenAI Whisper-specific options."""
    device: str = "cpu"  # cpu, cuda
    language: Optional[str] = None
    temperature: float = 0.0
    fp16: bool = False  # Use FP16 if GPU available

@dataclass
class Config:
    # ... existing fields ...
    backend: BackendConfig = field(default_factory=BackendConfig)
    vosk_options: VoskOptions = field(default_factory=VoskOptions)
    faster_whisper_options: FasterWhisperOptions = field(default_factory=FasterWhisperOptions)
    whisper_options: WhisperOptions = field(default_factory=WhisperOptions)
```

#### Example config.yaml:
```yaml
backend:
  type: faster-whisper

model:
  path: ~/.local/share/vosk-wrapper-1000/models/faster-whisper/base.en

faster_whisper_options:
  device: cuda
  compute_type: float16
  beam_size: 5
  language: en
  vad_filter: true
```

### 5. Model Manager Updates

Update `src/vosk_core/model_manager.py`:

```python
class ModelManager:
    def __init__(self):
        self.models_base_dir = get_models_dir()
        # Separate directories per backend
        self.vosk_models_dir = self.models_base_dir / "vosk"
        self.faster_whisper_models_dir = self.models_base_dir / "faster-whisper"
        self.whisper_models_dir = self.models_base_dir / "whisper"

    def resolve_model_path(self, model_path: str | Path, backend_type: str) -> Path:
        """Resolve model path based on backend type."""
        # Implementation: check backend-specific directory first
        pass

    def get_model_sample_rate(self, model_path: str, backend_type: str) -> int:
        """Get sample rate for model based on backend."""
        if backend_type == "vosk":
            # Read from mfcc.conf (existing logic)
            pass
        elif backend_type in ["faster-whisper", "whisper"]:
            # Whisper models expect 16kHz
            return 16000
        pass

    def validate_model(self, model_path: str, backend_type: str) -> tuple[bool, str]:
        """Validate model for specific backend."""
        # Backend-specific validation
        pass
```

### 6. Main Service Updates

Update `src/vosk_wrapper_1000/main.py`:

**Replace Vosk-specific code (lines 533-554):**

```python
# OLD:
import vosk
model = vosk.Model(str(args.model))
rec = vosk.KaldiRecognizer(model, model_sample_rate, args.grammar)

# NEW:
from vosk_core.backend_factory import create_backend

# Determine backend type
backend_type = args.backend or config.backend.type

# Get backend-specific options
if backend_type == "vosk":
    backend_options = {
        "words": config.vosk_options.words,
        "partial_words": config.vosk_options.partial_words,
        "grammar": config.vosk_options.grammar,
        "max_alternatives": config.vosk_options.max_alternatives,
    }
elif backend_type == "faster-whisper":
    backend_options = {
        "device": config.faster_whisper_options.device,
        "compute_type": config.faster_whisper_options.compute_type,
        "beam_size": config.faster_whisper_options.beam_size,
        "language": config.faster_whisper_options.language,
        "vad_filter": config.faster_whisper_options.vad_filter,
    }
elif backend_type == "whisper":
    backend_options = {
        "device": config.whisper_options.device,
        "language": config.whisper_options.language,
        "temperature": config.whisper_options.temperature,
        "fp16": config.whisper_options.fp16,
    }

# Create recognizer with backend
recognizer = create_backend(
    backend_type=backend_type,
    model_path=str(args.model),
    sample_rate=model_sample_rate,
    **backend_options
)
```

**Update recognition loop (lines 895-1022):**

```python
# OLD:
accepted = rec.AcceptWaveform(data)
if accepted:
    result = json.loads(rec.Result())
    text = result.get("text", "")
else:
    partial_result = json.loads(rec.PartialResult())
    partial_text = partial_result.get("partial", "")

# NEW:
accepted = recognizer.accept_waveform(data)
if accepted:
    result = recognizer.get_result()
    text = result.text
    confidence = result.confidence
else:
    partial_result = recognizer.get_partial_result()
    partial_text = partial_result.text

# ... handle speech end marker:
final_result = recognizer.get_final_result()
recognizer.reset()
```

### 7. CLI Argument Updates

Add to argument parser in `main.py`:

```python
parser.add_argument(
    "--backend",
    choices=["vosk", "faster-whisper", "whisper"],
    help="Recognition backend to use (overrides config file)"
)

# Vosk-specific args (only used with Vosk backend)
vosk_group = parser.add_argument_group("Vosk options")
vosk_group.add_argument("--words", action="store_true")
vosk_group.add_argument("--partial-words", action="store_true")
vosk_group.add_argument("--grammar")

# FasterWhisper-specific args
fw_group = parser.add_argument_group("FasterWhisper options")
fw_group.add_argument("--fw-device", choices=["cpu", "cuda", "auto"])
fw_group.add_argument("--fw-compute-type", choices=["int8", "float16", "float32"])
fw_group.add_argument("--fw-language")

# Whisper-specific args
whisper_group = parser.add_argument_group("Whisper options")
whisper_group.add_argument("--whisper-device", choices=["cpu", "cuda"])
whisper_group.add_argument("--whisper-language")
```

### 8. Dependencies Updates

Update `pyproject.toml`:

```toml
dependencies = [
    "vosk==0.3.44",
    # ... existing deps ...
]

[project.optional-dependencies]
pipewire = ["pipewire-python"]
faster-whisper = ["faster-whisper>=1.0.0"]
whisper = ["openai-whisper>=20230918"]
all-backends = [
    "faster-whisper>=1.0.0",
    "openai-whisper>=20230918",
]
```

### 9. Transcribe File Updates

Update `src/vosk_transcribe/main.py`:

```python
# Add backend selection
parser.add_argument(
    "--backend",
    choices=["vosk", "faster-whisper", "whisper"],
    default="vosk",
    help="Recognition backend to use"
)

# Use backend factory instead of direct Vosk
recognizer = create_backend(
    backend_type=args.backend,
    model_path=str(resolved_path),
    sample_rate=model_sample_rate,
)
```

## Implementation Steps

### Phase 1: Core Abstraction (Foundation)
1. Create `RecognitionResult` dataclass
2. Create `RecognitionBackend` ABC
3. Create `VoskBackend` implementation (wrap existing code)
4. Create `backend_factory.py` with registry
5. Add unit tests for VoskBackend

### Phase 2: Configuration System
1. Add `BackendConfig`, `VoskOptions` to config_manager.py
2. Update config loading/saving logic
3. Add CLI arguments for backend selection
4. Update environment variable overrides
5. Add tests for config loading

### Phase 3: Model Manager Updates
1. Create separate model directories structure
2. Update `resolve_model_path()` for multi-backend
3. Update `get_model_sample_rate()` for multi-backend
4. Update `validate_model()` for multi-backend
5. Add migration logic for existing Vosk models

### Phase 4: Main Service Integration
1. Replace Vosk import with backend factory
2. Update recognizer creation logic
3. Update recognition loop to use abstract interface
4. Update result handling (RecognitionResult)
5. Update IPC events to use RecognitionResult
6. Test with existing Vosk backend

### Phase 5: FasterWhisper Backend
1. Add faster-whisper dependency (optional)
2. Create `FasterWhisperBackend` class
3. Implement audio buffering for batch transcription
4. Add `FasterWhisperOptions` config
5. Add CLI arguments for FasterWhisper options
6. Test FasterWhisper integration

### Phase 6: Whisper Backend
1. Add openai-whisper dependency (optional)
2. Create `WhisperBackend` class
3. Implement audio buffering and transcription
4. Add `WhisperOptions` config
5. Add CLI arguments for Whisper options
6. Test Whisper integration

### Phase 7: Transcribe File Updates
1. Update vosk-transcribe to use backend factory
2. Add backend selection argument
3. Test with all three backends
4. Update documentation

### Phase 8: Documentation & Polish
1. Update README with backend selection instructions
2. Add backend-specific configuration examples
3. Update hooks documentation (if result format changes)
4. Add migration guide for existing users
5. Add backend comparison table (speed, accuracy, requirements)

## Testing Strategy

### Unit Tests
- Test each backend independently with sample audio
- Test RecognitionResult conversion from backend-specific formats
- Test backend factory with all backends
- Test config loading with backend-specific options

### Integration Tests
- Test main service with each backend
- Test transcribe file with each backend
- Test backend switching via config reload
- Test with different model types

### Manual Testing
- Test microphone input with each backend
- Test WebRTC audio with each backend
- Test IPC commands with different backends
- Test hooks with different result formats

## Migration Path for Existing Users

1. **Default behavior**: If no backend specified, default to "vosk" (backward compatible)
2. **Model location**: Existing models in `~/.local/share/vosk-wrapper-1000/models/` will be moved to `models/vosk/` automatically
3. **Config format**: Old configs without `backend` section will default to Vosk
4. **CLI compatibility**: All existing CLI arguments work as before (maps to vosk_options)

## Potential Challenges & Solutions

### Challenge 1: Whisper models don't support streaming
**Solution**: Buffer audio until speech end marker, then transcribe batch. Return empty partials or implement chunked processing.

### Challenge 2: Different sample rate requirements
**Solution**: Audio processor already handles resampling. Whisper expects 16kHz, which is common for Vosk too.

### Challenge 3: Backend-specific features (grammar, word timestamps)
**Solution**: Use optional fields in RecognitionResult. Backends return None for unsupported features. Document which features work with which backends.

### Challenge 4: Model format incompatibility
**Solution**: Separate model directories prevent confusion. Model manager validates model format against backend type.

### Challenge 5: GPU/CPU support varies by backend
**Solution**: Backend-specific options control device selection. Auto-detect GPU availability where possible.

## Success Criteria

- ✅ All three backends (Vosk, FasterWhisper, Whisper) work with daemon
- ✅ All three backends work with transcribe file tool
- ✅ Backend selection via config file and CLI argument
- ✅ Backend-specific options configurable
- ✅ Existing Vosk users can upgrade without breaking changes
- ✅ Tests pass for all backends
- ✅ Documentation updated with examples
- ✅ Model directories properly separated

## File Structure After Implementation

```
src/
├── vosk_core/
│   ├── recognition_backend.py          # NEW: Abstract base class
│   ├── backend_factory.py              # NEW: Factory and registry
│   ├── backends/                       # NEW: Backend implementations
│   │   ├── __init__.py
│   │   ├── vosk_backend.py            # NEW: Vosk wrapper
│   │   ├── faster_whisper_backend.py  # NEW: FasterWhisper wrapper
│   │   └── whisper_backend.py         # NEW: Whisper wrapper
│   ├── model_manager.py                # UPDATED: Multi-backend support
│   ├── audio_processor.py              # No changes needed
│   └── ...
├── vosk_wrapper_1000/
│   ├── main.py                         # UPDATED: Use backend factory
│   ├── config_manager.py               # UPDATED: Backend configs
│   └── ...
└── vosk_transcribe/
    └── main.py                         # UPDATED: Backend selection

~/.local/share/vosk-wrapper-1000/models/
├── vosk/                               # Vosk models (migrated)
│   └── vosk-model-small-en-us-0.15/
├── faster-whisper/                     # FasterWhisper models
│   ├── base.en/
│   └── medium.en/
└── whisper/                            # Whisper models
    ├── base.en.pt
    └── medium.en.pt
```

## Timeline Estimate

- **Phase 1-2** (Core + Config): 2-3 hours
- **Phase 3** (Model Manager): 1-2 hours
- **Phase 4** (Main Integration): 2-3 hours
- **Phase 5** (FasterWhisper): 2-3 hours
- **Phase 6** (Whisper): 2-3 hours
- **Phase 7** (Transcribe): 1 hour
- **Phase 8** (Docs/Polish): 2 hours

**Total**: ~12-18 hours of development work

## Next Steps

After approval:
1. Start with Phase 1: Create recognition_backend.py and VoskBackend
2. Get feedback on RecognitionResult interface
3. Proceed sequentially through phases
4. Test thoroughly at each phase before moving forward
