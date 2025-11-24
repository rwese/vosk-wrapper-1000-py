# Tests

This directory contains tests for vosk-wrapper-1000.

## Test Structure

- `unit/` - Unit tests for individual components
- `integration/` - Integration tests for component interactions
- `test_transcribe_e2e.py` - End-to-end tests for transcription functionality
- `conftest.py` - Shared pytest fixtures and configuration

## Test Model

The end-to-end tests use `vosk-model-en-gb-0.1` as the test model. This model is automatically downloaded when you run the tests if it's not already present in your models directory.

### Automatic Model Download

The `ensure_test_model_downloaded` fixture in `conftest.py` ensures the test model is available:

1. **Session-scoped**: The model is downloaded once per test session
2. **Automatic**: No manual intervention required
3. **Cached**: If the model exists, it's reused across test runs
4. **Configurable**: Change `TEST_MODEL` in `conftest.py` to use a different model

### Manual Model Download

To manually download the test model before running tests:

```bash
uv run vosk-download-model-1000 vosk-model-en-gb-0.1
```

## Running Tests

Run all tests:
```bash
uv run pytest
```

Run only end-to-end tests:
```bash
uv run pytest tests/test_transcribe_e2e.py
```

Run with verbose output to see model download progress:
```bash
uv run pytest tests/test_transcribe_e2e.py -v -s
```

## Test Assets

The `assets/` directory contains test audio files and expected transcripts:

- `transcript_test_1_input_stereo_44100hz_16bit_pcm.wav` - Test audio file (stereo, 44100 Hz)
- `transcript_test_1_transcript.txt` - Expected transcript for the test audio

## Adding New Tests

When adding new end-to-end tests that require the test model:

1. Import the model name from conftest: `from conftest import TEST_MODEL`
2. Add the fixture to your test function: `def test_my_feature(ensure_test_model_downloaded):`
3. Use `TEST_MODEL` in your commands instead of hardcoding the model name

Example:
```python
from conftest import TEST_MODEL

def test_my_transcription_feature(ensure_test_model_downloaded):
    cmd = [
        sys.executable,
        "-m",
        "vosk_wrapper_1000.main",
        "transcribe-file",
        "my_test_file.wav",
        "--model",
        TEST_MODEL,
    ]
    # ... rest of test
```

## Sample Rate Bug Fix

### The Bug

The daemon was recording audio that sounded "too slow" when played back. This was caused by a sample rate mismatch between the actual audio data and the WAV file header.

**Root Cause:** The `AudioProcessor` was initialized with placeholder sample rates (both 16000 Hz) before the actual device and model rates were known. Since the rates were equal during initialization, the soxr resampler was never created. When the rates were later updated to the correct values (e.g., device: 44100 Hz, model: 8000 Hz), the resampler remained `None`, causing raw microphone audio to be written with an incorrect sample rate header.

**Symptoms:**
- Audio recorded by daemon sounded slower than normal
- Example: microphone at 44100 Hz → recorded with 16000 Hz header → playback at 16000 Hz makes it sound 2.76x too slow
- `transcribe-file` command worked correctly because it initialized the `AudioProcessor` with correct rates from the start

**The Fix:**
Added resampler initialization after the correct rates are determined in `main.py:run_service()` (after line 355):

```python
# Initialize resampler now that we have the correct rates
if audio_processor.device_rate != audio_processor.model_rate:
    import soxr
    audio_processor.soxr_resampler = soxr.ResampleStream(
        in_rate=audio_processor.device_rate,
        out_rate=audio_processor.model_rate,
        num_channels=1,
        quality="HQ"
    )
    logger.info(f"Initialized resampler: {audio_processor.device_rate} Hz → {audio_processor.model_rate} Hz")
```

### Diagnostic Tools

- **`test_sample_rate_diagnosis.py`** - Comprehensive diagnostic tool for sample rate issues
- **`test_daemon_audio_capture.py`** - Simulates daemon audio capture to test microphone input
- **`test_audio_speed.py`** - Analyzes WAV files to detect sample rate mismatches
- **`test_sample_rate_bug.py`** - Reproduces the exact bug scenario
- **`test_resampler_fix.py`** - Verifies the fix works correctly
- **`test_daemon_recording_fixed.sh`** - End-to-end test of daemon recording after fix

### How to Test the Fix

1. **Verify the fix works:**
   ```bash
   python tests/test_resampler_fix.py
   ```

2. **Test daemon recording (requires microphone):**
   ```bash
   ./tests/test_daemon_recording_fixed.sh
   ```

3. **Analyze a recording to check for sample rate issues:**
   ```bash
   python tests/test_audio_speed.py ~/path/to/recording.wav
   ```

4. **Full microphone diagnostics:**
   ```bash
   python tests/test_sample_rate_diagnosis.py
   ```

### Expected Results After Fix

- ✓ Daemon recordings have correct sample rate in WAV header
- ✓ Audio plays back at normal speed
- ✓ No "too slow" or "too fast" playback issues
- ✓ Device sample rate (e.g., 44100 Hz) is properly resampled to model rate (e.g., 8000 Hz or 16000 Hz)

### Understanding Sample Rate Issues

**Sample Rate Relationships:**
- If actual audio data rate > header rate → sounds **TOO SLOW**
- If actual audio data rate < header rate → sounds **TOO FAST**
- Example: 44100 Hz data with 16000 Hz header = 2.76x too slow

**Why this happens:**
1. Microphone captures at device rate (e.g., 44100 Hz)
2. Audio should be resampled to model rate (e.g., 8000 Hz)
3. If resampling is skipped, raw 44100 Hz data is written to file
4. WAV header incorrectly says 8000 Hz
5. Player reads at 8000 Hz but data is actually 44100 Hz
6. Playback takes 44100/8000 = 5.5x longer → sounds very slow

### Key Learnings

1. **Initialization Order Matters** - Resources that depend on configuration must be created AFTER configuration is finalized. Updating attributes doesn't retroactively create dependent resources.

2. **Test with Different Configurations** - Test with different models (8000 Hz vs 16000 Hz) and microphone sample rates (44100 Hz, 48000 Hz) to catch edge cases.

3. **Verify Both Header and Content** - Always check both the WAV header AND actual playback speed when debugging audio issues.
