# Audio Processing Pipeline

This document describes the complete audio pre-processing pipeline in
vosk-wrapper-1000, from raw microphone input to speech recognition.

## Overview

The audio processing system implements a sophisticated multi-stage pipeline
that:
- Handles any device sample rate and converts to model requirements
- Filters out noise while preserving speech quality
- Detects voice activity to avoid processing silence
- Buffers audio before speech starts to avoid cutting off words
- Normalizes audio levels for consistent recognition

## Complete Processing Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     AUDIO PROCESSING PIPELINE                       │
└─────────────────────────────────────────────────────────────────────┘

1. AUDIO INPUT (from sounddevice)
    └─> Raw audio chunks at device native rate (e.g., 48kHz)
        Format: int16, mono/stereo, 1024 samples per chunk
        Location: main.py:628-671 (audio_callback)

2. MONO CONVERSION (if needed)
    └─> Convert stereo to mono by averaging channels
        Location: main.py:394-398

3. PRE-PROCESSING STAGE (AudioProcessor.process_with_vad)
    │   Location: audio_processor.py:304-387
    │
    ├─> 3a. AUDIO PROCESSING (_process_mono_audio_chunk)
    │   │   Location: audio_processor.py:178-257
    │   │
    │   ├─> [Optional] NORMALIZATION (normalize_audio_chunk)
    │   │   └─> Adjusts audio levels to target RMS
    │   │       - Removes DC offset
    │   │       - Calculates current RMS
    │   │       - Applies gain to reach target level (default: 0.3)
    │   │       - Limits max gain to 50x to prevent over-amplification
    │   │       Location: audio_processor.py:83-127
    │   │
    │   ├─> [Optional] NOISE REDUCTION
    │   │   └─> Filters out background noise while preserving speech
    │   │       - Uses noisereduce library
    │   │       - Stationary (fast) or non-stationary (adaptive) mode
    │   │       - Strength configurable (0.0-1.0, default: 0.05)
    │   │       - Validates reduction didn't remove too much signal
    │   │         (min RMS ratio: 0.5)
    │   │       - Reverts to original if over-aggressive
    │   │       Location: audio_processor.py:196-240
    │   │
    │   └─> [Optional] RESAMPLING
    │       └─> Converts from device rate to model rate
    │           - Uses soxr HQ streaming resampler
    │           - High-quality algorithm with proper chunking
    │           - Example: 48kHz device → 16kHz model
    │           Location: audio_processor.py:242-255
    │
    └─> 3b. VOICE ACTIVITY DETECTION (VAD)
        │   Location: audio_processor.py:329-387
        │
        ├─> SILENCE DETECTION (has_audio)
        │   └─> Checks if audio contains meaningful sound
        │       - Calculates RMS energy after removing DC offset
        │       - Compares to silence threshold (default: 50.0)
        │       - Performed on PROCESSED audio (after noise reduction)
        │       Location: audio_processor.py:63-81
        │
        ├─> PRE-ROLL BUFFERING
        │   └─> Ring buffer for audio before speech detection
        │       - Stores unprocessed audio chunks
        │       - Configurable duration (default: 2.0 seconds)
        │       - Processes and flushes when speech detected
        │       - Prevents cutting off word beginnings
        │       Location: audio_processor.py:40-48, 271-302
        │
        └─> STATE MACHINE
            ├─> SILENCE → SPEECH transition
            │   - Flush pre-roll buffer (process all buffered chunks)
            │   - Return pre-roll audio + current chunk
            │   - Set in_speech = True
            │
            ├─> SPEECH continuation
            │   - Return current chunk
            │   - Reset consecutive_silent_chunks counter
            │
            ├─> SPEECH with silence (hysteresis)
            │   - Allow N silent chunks (default: 10)
            │   - Continue sending chunks during hysteresis
            │   - Natural pauses in speech don't end detection
            │
            └─> SPEECH → SILENCE transition
                - After hysteresis_chunks consecutive silence
                - Set in_speech = False, speech_just_ended = True
                - Clear pre-roll buffer
                - Return empty list (no chunks)

4. QUEUE FOR VOSK
    └─> Processed chunks added to thread-safe queue
        - Non-blocking put_nowait (drops if queue full)
        - Special SPEECH_END_MARKER when speech ends
        Location: main.py:664, 653

5. VOSK RECOGNITION
    └─> Main loop consumes queue and feeds to recognizer
        - AcceptWaveform processes audio
        - Partial results during speech
        - Final result when speech ends or waveform completes
        Location: main.py:897-1022
```

## Processing Steps in Detail

### 1. Audio Input

Audio is captured by the `sounddevice` library (PortAudio wrapper) at the
device's native sample rate:

```python
# Create audio stream at device native rate
stream = sd.InputStream(
    samplerate=device_samplerate,  # e.g., 48000 Hz
    blocksize=1024,                 # 1024 samples per callback
    device=device_id,
    dtype="int16",
    channels=1,
    callback=audio_callback
)
```

**Key Points:**
- Always uses device's native sample rate (no forcing)
- Fixed blocksize of 1024 samples for consistent chunking
- int16 format for efficient processing

### 2. Mono Conversion

If the input has multiple channels, convert to mono by averaging:

```python
if channels > 1:
    raw_mono = np.mean(indata, axis=1)
else:
    raw_mono = indata[:, 0]
```

**Location:** main.py:394-398, audio_processor.py:435-439

### 3. Audio Normalization (Optional)

Normalizes audio to a consistent RMS level before other processing:

**Process:**
1. Convert to float and remove DC offset
2. Calculate current RMS energy
3. Calculate gain needed to reach target RMS (default: 0.3)
4. Apply gain with max limit of 50x
5. Clip and convert back to int16

**Purpose:**
- Ensures consistent volume levels across different microphones
- Helps quiet speech be better recognized
- Prevents over-amplification of very quiet audio

**Important: Normalization happens BEFORE silence detection!**

This means normalization affects Voice Activity Detection:
```
Example with --silence-threshold 50.0:

WITHOUT normalization:
  Raw audio RMS=30 → Silence check → BELOW threshold → Not detected ✗

WITH normalization (target=0.3 ≈ RMS 9830):
  Raw audio RMS=30 → Normalize → RMS=9830 → Silence check → ABOVE
  threshold → Detected ✓
```

**When to enable:**
- Microphone is far from speaker
- User speaks quietly
- Multiple users with different volumes
- Need consistent detection regardless of volume

**When to disable:**
- High background noise (normalization amplifies noise too)
- Microphone is very close and loud
- Using other volume control (AGC, hardware gain)

**Configuration:**
```bash
# Enable with default target (0.3 RMS in float = ~9830 in int16)
vosk-wrapper-1000 daemon --normalize-audio

# Adjust target level (higher = louder)
vosk-wrapper-1000 daemon --normalize-audio --normalize-target-level 0.4

# Combine with adjusted silence threshold
vosk-wrapper-1000 daemon --normalize-audio --silence-threshold 100.0
```

**Location:** audio_processor.py:83-127

### 4. Noise Reduction (Optional)

Uses the `noisereduce` library to filter background noise while preserving
speech:

**Process:**
1. Convert to float32 normalized to [-1.0, 1.0]
2. Apply noise reduction algorithm
3. Check that RMS wasn't reduced too much (min ratio: 0.5)
4. If reduction was too aggressive, revert to original
5. Convert back to int16

**Modes:**
- **Stationary** (default): Fast, assumes constant background noise
- **Non-stationary**: Slower, adapts to changing noise patterns

**Configuration:**
```bash
# Basic noise reduction
vosk-wrapper-1000 daemon --noise-reduction 0.05

# Stronger reduction
vosk-wrapper-1000 daemon --noise-reduction 0.3

# Non-stationary mode for variable environments
vosk-wrapper-1000 daemon --non-stationary-noise --noise-reduction 0.2

# Disable noise reduction
vosk-wrapper-1000 daemon --disable-noise-reduction
```

**Safety Check:**
The system validates that noise reduction doesn't remove too much signal by
comparing RMS before and after. If processed RMS falls below
`noise_reduction_min_rms_ratio` (default: 0.5) of the original, the original
audio is used instead.

**Location:** audio_processor.py:196-240

### 5. Resampling (Automatic)

Converts audio from device rate to model rate using soxr HQ streaming:

**Process:**
1. Convert to float32 normalized to [-1.0, 1.0]
2. Reshape to (samples, 1) for soxr
3. Stream through soxr.ResampleStream with "HQ" quality
4. Flatten and convert back to int16

**Example:**
- Device: 48000 Hz → Model: 16000 Hz
- 1024 samples at 48kHz → ~341 samples at 16kHz

**Benefits of soxr:**
- High-quality algorithm better than scipy
- Streaming resampler maintains state across chunks
- Efficient real-time processing

**Initialization:**
```python
if device_rate != model_rate:
    self.soxr_resampler = soxr.ResampleStream(
        in_rate=device_rate,
        out_rate=model_rate,
        num_channels=1,
        quality="HQ"
    )
```

**Location:** audio_processor.py:58-61, 242-255

### 6. Voice Activity Detection (VAD)

The VAD system is a sophisticated state machine that intelligently detects
when speech is present while avoiding false triggers from background noise and
handling natural pauses in speech.

#### 6.1 Silence Detection

The fundamental building block of VAD is the silence detector that determines
if an audio chunk contains meaningful sound:

```python
def has_audio(self, audio_data: np.ndarray) -> bool:
    """Check if audio contains meaningful sound above silence threshold."""
    if len(audio_data) == 0:
        return False

    # Convert to float for calculation
    audio_float = audio_data.astype(np.float32)

    # Remove DC offset (constant bias in signal)
    # This ensures we measure actual audio energy, not microphone bias
    audio_float = audio_float - np.mean(audio_float)

    # Calculate RMS (Root Mean Square) energy
    # RMS is a good measure of the "loudness" of the signal
    rms = np.sqrt(np.mean(audio_float**2))

    # Compare to silence threshold
    return rms > self.silence_threshold
```

**Why RMS?**
- RMS measures the effective energy of the audio signal
- More robust than peak detection (ignores brief spikes)
- Better represents perceived loudness than simple averaging

**Why Remove DC Offset?**
- Microphones can have a constant voltage offset
- DC offset biases RMS calculation
- Removing it ensures we measure actual audio variation

**Important:** Silence detection is performed on **PROCESSED** audio (after
normalization and noise reduction), not raw audio. This is critical because:
1. **Normalization (if enabled)** amplifies quiet speech to detectable levels
2. **Noise reduction (if enabled)** removes background noise that could cause
false negatives
3. **Resampling** provides consistent sample rate for threshold comparison

**Processing Order for Silence Detection:**
```
Raw Audio → [Normalization] → [Noise Reduction] → [Resampling] → Silence
Detection (has_audio)
                    ↓                  ↓                 ↓
              Amplifies quiet    Removes background   Model rate
              speech first       noise                for RMS calc
```

This means:
- **With normalization enabled:** Quiet/distant speech is amplified BEFORE
silence detection, making it more likely to be detected
- **Without normalization:** Only the original audio volume is considered
- The `--silence-threshold` value interacts with normalization settings

**Configuration:**
```bash
vosk-wrapper-1000 daemon --silence-threshold 50.0
```

**Typical RMS Values:**
- Silence/background noise: 0-50
- Quiet speech: 50-200
- Normal speech: 200-1000
- Loud speech: 1000-5000

**Location:** audio_processor.py:63-81

#### 6.2 Pre-Roll Buffering

Pre-roll buffering is a ring buffer that continuously stores audio **before**
speech is detected, ensuring we never cut off the beginning of words.

**The Problem Without Pre-Roll:**
```
Timeline:    |----silence----|---SPEECH STARTS---|---speech---|
Detection:                         ^
                                   |
                             Detected here!
                             (beginning of word already lost)
```

**The Solution With Pre-Roll:**
```
Timeline:    |----silence----|---SPEECH STARTS---|---speech---|
Buffer:      [store][store][store][store][store]
Detection:                         ^
                                   |
                             Detected here!
                             (flush buffer to get beginning)
Output:      [buffered audio][---SPEECH STARTS---|---speech---|
```

**Implementation Details:**

```python
# Ring buffer for pre-roll audio
self.pre_roll_buffer: deque[np.ndarray] = deque(maxlen=200)
self.pre_roll_samples = int(pre_roll_duration * model_rate)

# Example: 2.0 seconds at 16kHz = 32,000 samples
# At 1024 samples per chunk after resampling = ~31 chunks
# Buffer maxlen=200 can hold ~6.4 seconds of audio
```

**Why Store Unprocessed Audio?**
The buffer stores **raw mono audio** (before noise reduction/resampling) for
two reasons:
1. **Avoid cumulative artifacts:** Processing audio multiple times accumulates
distortion
2. **Efficiency:** Only process audio once when it's actually needed
3. **Flexibility:** Can apply different processing settings to buffered audio

**Buffer Processing on Speech Detection:**

```python
def get_pre_roll_audio(self) -> np.ndarray:
    """Process and return accumulated pre-roll audio."""
    # 1. Iterate through all buffered chunks
    processed_chunks = []
    for chunk in self.pre_roll_buffer:
        # 2. Process each chunk (normalization, noise reduction, resampling)
        processed_chunk = self._process_mono_audio_chunk(chunk)
        if len(processed_chunk) > 0:
            processed_chunks.append(processed_chunk)

    # 3. Concatenate all processed chunks
    buffered_audio = np.concatenate(processed_chunks)

    # 4. Trim to pre_roll_duration (keep only most recent samples)
    if len(buffered_audio) > self.pre_roll_samples:
        buffered_audio = buffered_audio[-self.pre_roll_samples:]

    return buffered_audio
```

**Buffer Management:**
- **Ring buffer (deque):** Automatically drops oldest chunks when full
- **Max capacity:** 200 chunks (~6.4 seconds at 16kHz)
- **Typical usage:** 2.0 seconds = ~31 chunks
- **Memory:** ~6 MB for 2 seconds at 48kHz (unprocessed)

**Configuration:**
```bash
# Store 2.0 seconds of audio before speech detection
vosk-wrapper-1000 daemon --pre-roll-duration 2.0

# Increase for very slow speakers or delayed response
vosk-wrapper-1000 daemon --pre-roll-duration 3.0

# Decrease for faster response (may cut off word beginnings)
vosk-wrapper-1000 daemon --pre-roll-duration 1.0
```

**Location:** audio_processor.py:40-48, 271-302

#### 6.3 VAD State Machine

The VAD implements a finite state machine with hysteresis to robustly handle
speech detection:

**State Variables:**
```python
self.in_speech = False                    # Currently in a speech segment?
self.consecutive_silent_chunks = 0        # Counter for hysteresis
self.speech_just_ended = False            # Flag for main loop
self.pre_roll_buffer = deque(maxlen=200)  # Ring buffer for pre-roll
```

**State Diagram:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         VAD STATE MACHINE                               │
└─────────────────────────────────────────────────────────────────────────┘

                                    ┌─────────────┐
                                    │   INITIAL   │
                                    │  in_speech  │
                                    │   = False   │
                                    └──────┬──────┘
                                           │
                                           │ (system start)
                                           v
    ┌──────────────────────────────────────────────────────────────────┐
    │                                                                  │
    │  ┌───────────────────────────────────────────────────────────┐  │
    │  │                    STATE 1: IDLE                          │  │
    │  │  in_speech = False                                        │  │
    │  │  consecutive_silent_chunks = 0                            │  │
    │  ├───────────────────────────────────────────────────────────┤  │
    │  │  Actions:                                                 │  │
    │  │  - Store audio in pre_roll_buffer                         │  │
    │  │  - Check has_audio() on processed audio                   │  │
    │  │  - Return empty list (nothing to Vosk)                    │  │
    │  └────────────────┬──────────────────────────────────────────┘  │
    │                   │                                              │
    │                   │ has_audio() = True                           │
    │                   │ (speech detected!)                           │
    │                   v                                              │
    │  ┌───────────────────────────────────────────────────────────┐  │
    │  │          STATE 2: SPEECH START                            │  │
    │  │  in_speech = False → True                                 │  │
    │  ├───────────────────────────────────────────────────────────┤  │
    │  │  Actions:                                                 │  │
    │  │  1. Process entire pre_roll_buffer                        │  │
    │  │  2. Return [pre_roll_audio, current_chunk]                │  │
    │  │  3. Clear pre_roll_buffer                                 │  │
    │  │  4. Set in_speech = True                                  │  │
    │  │  5. Reset consecutive_silent_chunks = 0                   │  │
    │  └────────────────┬──────────────────────────────────────────┘  │
    │                   │                                              │
    │                   v                                              │
    │  ┌───────────────────────────────────────────────────────────┐  │
    │  │          STATE 3: ACTIVE SPEECH                           │  │
    │  │  in_speech = True                                         │  │
    │  │  consecutive_silent_chunks = 0                            │  │
    │  ├───────────────────────────────────────────────────────────┤  │
    │  │  Actions:                                                 │  │
    │  │  - Return [current_chunk] to Vosk                         │  │
    │  │  - Reset consecutive_silent_chunks = 0                    │  │
    │  │  - Continue as long as has_audio() = True                 │  │
    │  └────────────────┬──────────────────┬───────────────────────┘  │
    │                   │                  │                          │
    │                   │                  │ has_audio() = False      │
    │                   │                  │ (pause in speech)        │
    │                   │                  v                          │
    │                   │  ┌──────────────────────────────────────┐  │
    │                   │  │     STATE 4: HYSTERESIS              │  │
    │                   │  │  in_speech = True                    │  │
    │                   │  │  consecutive_silent_chunks++         │  │
    │                   │  ├──────────────────────────────────────┤  │
    │                   │  │  Actions:                            │  │
    │                   │  │  - Increment silent chunk counter    │  │
    │                   │  │  - IF counter ≤ vad_hysteresis:      │  │
    │                   │  │    * Return [current_chunk] to Vosk  │  │
    │                   │  │    * Stay in speech mode             │  │
    │                   │  │  - ELSE:                             │  │
    │                   │  │    * Transition to STATE 5           │  │
    │                   │  └───────────┬────────────┬─────────────┘  │
    │                   │              │            │                 │
    │                   │              │            │ counter >       │
    │      has_audio()  │              │            │ vad_hysteresis  │
    │      = True       │              │            v                 │
    │      (speech      │              │  ┌─────────────────────────┐ │
    │      resumes)     │              │  │   STATE 5: SPEECH END   │ │
    │                   │              │  │  in_speech = True→False │ │
    │                   └──────────────┘  ├─────────────────────────┤ │
    │      (reset counter = 0)            │  Actions:               │ │
    │                                     │  - Set in_speech=False  │ │
    │                                     │  - Set speech_just_     │ │
    │                                     │    ended = True         │ │
    │                                     │  - Clear pre_roll_buffer│ │
    │                                     │  - Reset counters       │ │
    │                                     │  - Return empty list    │ │
    │                                     └────────┬────────────────┘ │
    │                                              │                  │
    │                                              │ (back to idle)   │
    └──────────────────────────────────────────────┼──────────────────┘
                                                   │
                                                   v
                                           (return to STATE 1)
```

**Detailed State Descriptions:**

**STATE 1: IDLE (Waiting for Speech)**
```python
# State variables
in_speech = False
consecutive_silent_chunks = 0

# Processing
processed_audio = self._process_mono_audio_chunk(mono_audio)
has_audio = self.has_audio(processed_audio)

if not has_audio and not in_speech:
    # Store unprocessed audio for potential pre-roll
    self.pre_roll_buffer.append(mono_audio.copy())
    return []  # Nothing to Vosk
```

**Example:**
```
Chunk 1: RMS=25  (< threshold=50)  → Buffer, return []
Chunk 2: RMS=30  (< threshold=50)  → Buffer, return []
Chunk 3: RMS=45  (< threshold=50)  → Buffer, return []
```

**STATE 2: SPEECH START (Transition)**
```python
if has_audio and not in_speech:
    # Flush pre-roll buffer
    pre_roll = self.get_pre_roll_audio()
    result = []
    if len(pre_roll) > 0:
        result.append(pre_roll)

    # Set speech mode
    in_speech = True
    self.pre_roll_buffer.clear()
    consecutive_silent_chunks = 0

    # Add current chunk
    result.append(processed_audio)
    return result  # [pre_roll, current] to Vosk
```

**Example:**
```
Chunk 4: RMS=150 (> threshold=50)  → Process buffer chunks 1-3, return
[pre_roll, chunk_4]
                                      Set in_speech = True
```

**STATE 3: ACTIVE SPEECH (Continuous)**
```python
if has_audio and in_speech:
    # Reset hysteresis counter
    consecutive_silent_chunks = 0

    # Continue sending audio
    return [processed_audio]  # [current] to Vosk
```

**Example:**
```
Chunk 5: RMS=850 (> threshold=50)  → Return [chunk_5]
Chunk 6: RMS=920 (> threshold=50)  → Return [chunk_6]
Chunk 7: RMS=780 (> threshold=50)  → Return [chunk_7]
```

**STATE 4: HYSTERESIS (Natural Pause)**

This is the key to handling natural speech patterns!

```python
if not has_audio and in_speech:
    consecutive_silent_chunks += 1

    if consecutive_silent_chunks <= vad_hysteresis_chunks:
        # Within hysteresis window - continue sending audio
        # This allows natural pauses without ending speech
        return [processed_audio]  # [current] to Vosk
    else:
        # Exceeded hysteresis - speech has ended
        # → Transition to STATE 5
```

**Example with vad_hysteresis_chunks=10:**
```
Chunk 8:  RMS=720 (> threshold)  → consecutive_silent=0, return [chunk_8]
Chunk 9:  RMS=40  (< threshold)  → consecutive_silent=1, return [chunk_9]
(hysteresis)
Chunk 10: RMS=35  (< threshold)  → consecutive_silent=2, return [chunk_10]
(hysteresis)
Chunk 11: RMS=42  (< threshold)  → consecutive_silent=3, return [chunk_11]
(hysteresis)
Chunk 12: RMS=650 (> threshold)  → consecutive_silent=0, return [chunk_12]
(speech resumed!)
```

**Why Hysteresis is Critical:**
- **Natural pauses:** People pause between words/sentences
- **Breathing:** Brief silent periods during breathing
- **Consonants:** Some speech sounds have lower energy
- **Without hysteresis:** Each pause would end detection, creating fragmented
results

**Timing Example:**
```
Chunk duration: 1024 samples @ 16kHz = 64ms
Hysteresis: 10 chunks = 640ms

This allows pauses up to 0.64 seconds without ending speech detection!
```

**STATE 5: SPEECH END (Transition Back)**
```python
if consecutive_silent_chunks > vad_hysteresis_chunks:
    # Speech has ended
    in_speech = False
    consecutive_silent_chunks = 0
    speech_just_ended = True  # Signal to main loop
    self.pre_roll_buffer.clear()
    return []  # Nothing to Vosk
```

**Example:**
```
Chunks 13-22: RMS < threshold (10 consecutive silent chunks)
Chunk 23: consecutive_silent=11 > vad_hysteresis=10
          → Set in_speech = False
          → Set speech_just_ended = True
          → Clear buffer
          → Return []
```

**speech_just_ended Flag:**

This flag signals the main loop to finalize the recognition:
```python
# In main.py audio processing loop
if audio_processor.check_and_reset_speech_end():
    # Speech ended - finalize current utterance
    audio_queue.put_nowait(SPEECH_END_MARKER)
```

The main loop receives the marker and:
1. Calls `rec.FinalResult()` to get final transcription
2. Prints/broadcasts the result
3. Resets recognizer with `rec.Reset()`

**Configuration:**
```bash
# Default: Allow 640ms of silence before ending speech
vosk-wrapper-1000 daemon --vad-hysteresis 10

# More aggressive (faster end detection, may fragment speech)
vosk-wrapper-1000 daemon --vad-hysteresis 5

# More lenient (longer pauses allowed, may delay end detection)
vosk-wrapper-1000 daemon --vad-hysteresis 15
```

**Hysteresis Calculation:**
```python
# Calculate actual time delay
chunk_duration = blocksize / model_rate  # 1024 / 16000 = 0.064 seconds
hysteresis_time = chunk_duration * vad_hysteresis_chunks

# Examples:
# vad_hysteresis=10 → 0.064 * 10 = 0.64 seconds
# vad_hysteresis=5  → 0.064 * 5  = 0.32 seconds
# vad_hysteresis=15 → 0.064 * 15 = 0.96 seconds
```

**Location:** audio_processor.py:304-387, 389-397, 399-407

### 7. Queue Management

Processed audio chunks are queued for Vosk recognition:

**Process:**
- Non-blocking `put_nowait()` to avoid callback blocking
- Drops frames if queue is full (prevents audio overflow)
- Special `SPEECH_END_MARKER` inserted when speech ends
- Main loop consumes queue with 0.1s timeout

**Location:** main.py:621, 664, 653, 897

### 8. Speech Recognition

Main loop feeds queued audio to Vosk recognizer:

**Process:**
1. Get chunk from queue (timeout: 0.1s)
2. Check for SPEECH_END_MARKER
   - If marker: call `rec.FinalResult()` and reset
3. Otherwise: call `rec.AcceptWaveform(data)`
   - If accepted (final result): print and broadcast
   - If not accepted: send partial result to IPC clients

**Location:** main.py:895-1027

## Configuration Parameters

All audio processing parameters are configurable via command-line arguments:

### Normalization
```bash
--normalize-audio                    # Enable audio normalization
--normalize-target-level 0.3         # Target RMS level (0.0-1.0)
```

### Noise Reduction
```bash
--disable-noise-reduction            # Disable noise filtering
--noise-reduction-level 0.05         # Strength (0.0-1.0, default: 0.05)
--stationary-noise                   # Fast, constant noise
--non-stationary-noise               # Adaptive, variable noise
--noise-reduction-min-rms-ratio 0.5  # Safety threshold
```

### Voice Activity Detection
```bash
--silence-threshold 50.0             # RMS threshold for audio detection
--vad-hysteresis 10                  # Silent chunks before ending speech
--pre-roll-duration 2.0              # Seconds to buffer before speech
```

### Recording
```bash
--record-audio output.wav            # Record processed audio for review
```

## Performance Considerations

### CPU Usage
- **Without noise reduction:** ~10-15% CPU during listening
- **With noise reduction (stationary):** ~20-25% CPU
- **With noise reduction (non-stationary):** ~30-40% CPU
- **Resampling (soxr):** Minimal overhead, ~1-2% CPU

### Latency
- **Audio callback:** ~21ms per chunk (1024 samples @ 48kHz)
- **Processing:** <5ms per chunk (noise + resample)
- **Pre-roll delay:** 0ms (buffering happens continuously)
- **Total latency:** ~50-100ms from speech to recognition start

### Memory
- **Pre-roll buffer:** ~3-6 MB (2 seconds @ 16kHz)
- **Audio queue:** Minimal, drops frames if overloaded
- **Model:** 100MB - 7GB depending on model size

## Audio Recording for Debugging

Record exactly what Vosk receives for review:

```bash
vosk-wrapper-1000 daemon --record-audio session.wav
```

The recording includes:
- All processing (normalization, noise reduction, resampling)
- Only audio sent to Vosk (respects VAD)
- Useful for debugging recognition issues

**Location:** audio_recorder.py, main.py:660-661

## Common Issues and Solutions

### Issue: Words cut off at the beginning

**Solution:** Increase pre-roll duration
```bash
vosk-wrapper-1000 daemon --pre-roll-duration 3.0
```

### Issue: Recognition continues during pauses

**Solution:** Decrease VAD hysteresis
```bash
vosk-wrapper-1000 daemon --vad-hysteresis 5
```

### Issue: Speech not detected

**Understanding the Problem:**

Silence detection happens AFTER audio processing, so the order matters:
```
Raw Audio (RMS=30) → Normalization (RMS=200) → Silence Check
(threshold=50) → DETECTED ✓
Raw Audio (RMS=30) → No Normalization        → Silence Check
(threshold=50) → NOT DETECTED ✗
```

**Solutions:**

1. **Enable normalization to amplify quiet audio** (recommended first step)
   ```bash
   vosk-wrapper-1000 daemon --normalize-audio --normalize-target-level 0.3
   ```
    This amplifies quiet speech BEFORE silence detection, making it more
    likely to be detected.

2. **Lower silence threshold** (if normalization doesn't help)
   ```bash
   vosk-wrapper-1000 daemon --silence-threshold 30.0
   ```
   Use this if speech is genuinely quiet even after normalization.

3. **Combine both approaches** (for very quiet environments)
   ```bash
   vosk-wrapper-1000 daemon --normalize-audio --silence-threshold 30.0
   ```

4. **Record and review audio to diagnose**
   ```bash
   vosk-wrapper-1000 daemon --record-audio debug.wav --normalize-audio
   ```
    Listen to what Vosk receives. If it's still too quiet, increase
    normalization target or lower threshold.

### Issue: Too much background noise

**Solutions:**
1. Increase noise reduction
   ```bash
   vosk-wrapper-1000 daemon --noise-reduction 0.3
   ```

2. Use non-stationary mode for variable noise
   ```bash
   vosk-wrapper-1000 daemon --non-stationary-noise
   ```

3. Adjust minimum RMS ratio if speech is being filtered
   ```bash
   vosk-wrapper-1000 daemon --noise-reduction-min-rms-ratio 0.3
   ```

## Code References

- **AudioProcessor:** src/vosk_core/audio_processor.py
- **Main audio callback:** src/vosk_wrapper_1000/main.py:628-671
- **Audio recorder:** src/vosk_core/audio_recorder.py
- **Device management:** src/vosk_core/device_manager.py
- **Model management:** src/vosk_core/model_manager.py

## See Also

- [ARCHITECTURE.md](../ARCHITECTURE.md) - Overall system architecture
- [CONFIGURATION.md](CONFIGURATION.md) - Configuration file reference
- [README.md](../README.md) - Quick start and usage examples
