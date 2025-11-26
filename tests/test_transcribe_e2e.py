#!/usr/bin/env python3
"""End-to-end test for transcribe-file command with real audio assets."""

import subprocess
import sys
from pathlib import Path

import pytest

# Import shared test configuration
from conftest import TEST_MODEL

# Determine project root and test assets directory
TEST_DIR = Path(__file__).parent
PROJECT_ROOT = TEST_DIR.parent
ASSETS_DIR = TEST_DIR / "assets"
TRANSCRIPT_AUDIO = ASSETS_DIR / "transcript_test_1_input_stereo_44100hz_16bit_pcm.wav"
EXPECTED_TRANSCRIPT = ASSETS_DIR / "transcript_test_1_transcript.txt"

# Test 2: Audio with background noise (mono, 48kHz)
TRANSCRIPT_AUDIO_2 = (
    ASSETS_DIR / "transcript_test_2_with_background_noise_mono_48000hz_16bit.wav"
)
EXPECTED_TRANSCRIPT_2 = (
    ASSETS_DIR
    / "transcript_test_2_with_background_noise_mono_48000hz_16bit_transcript.txt"
)


@pytest.mark.skipif(not TRANSCRIPT_AUDIO.exists(), reason="Test audio file not found")
@pytest.mark.skipif(
    not EXPECTED_TRANSCRIPT.exists(), reason="Expected transcript file not found"
)
def test_transcribe_file_e2e(ensure_test_model_downloaded):
    """Test the transcribe-file command end-to-end with real audio."""
    # Read expected transcript
    with open(EXPECTED_TRANSCRIPT) as f:
        expected_text = f.read().strip()

    # Run transcribe-file command
    cmd = [
        sys.executable,
        "-m",
        "vosk_wrapper_1000.main",
        "transcribe-file",
        str(TRANSCRIPT_AUDIO),
        "--model",
        TEST_MODEL,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    # Check that command succeeded
    assert result.returncode == 0, f"Command failed: {result.stderr}"

    # The transcript is printed to stdout (first line), while logging goes to stderr
    # Extract just the first line from stdout which contains the transcript
    stdout_lines = [line for line in result.stdout.strip().split("\n") if line.strip()]

    # The first non-empty line should be the transcript
    actual_transcript = stdout_lines[0].strip() if stdout_lines else ""

    # Compare with expected (allowing for minor differences in transcription)
    # The model might produce slightly different results, so we check for key words
    expected_words = set(expected_text.lower().split())
    actual_words = set(actual_transcript.lower().split())

    # Check that most words match (at least 80% overlap)
    common_words = expected_words & actual_words
    word_match_ratio = len(common_words) / len(expected_words) if expected_words else 0

    assert word_match_ratio >= 0.8, (
        f"Transcript mismatch. Expected: '{expected_text}', "
        f"Got: '{actual_transcript}' (match ratio: {word_match_ratio:.2%})"
    )


@pytest.mark.skipif(not TRANSCRIPT_AUDIO.exists(), reason="Test audio file not found")
def test_transcribe_file_with_silence_threshold(ensure_test_model_downloaded):
    """Test transcribe-file with different silence threshold values."""
    # Test with default threshold (50.0)
    cmd_default = [
        sys.executable,
        "-m",
        "vosk_wrapper_1000.main",
        "transcribe-file",
        str(TRANSCRIPT_AUDIO),
        "--model",
        TEST_MODEL,
    ]

    result_default = subprocess.run(
        cmd_default,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    assert result_default.returncode == 0, (
        f"Default threshold failed: {result_default.stderr}"
    )

    # Test with aggressive threshold (25.0)
    cmd_aggressive = [
        sys.executable,
        "-m",
        "vosk_wrapper_1000.main",
        "transcribe-file",
        str(TRANSCRIPT_AUDIO),
        "--model",
        "vosk-model-en-gb-0.1",
        "--silence-threshold",
        "25.0",
    ]

    result_aggressive = subprocess.run(
        cmd_aggressive,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    assert result_aggressive.returncode == 0, (
        f"Aggressive threshold failed: {result_aggressive.stderr}"
    )

    # Both should produce output (transcripts go to stdout)
    assert result_default.stdout.strip(), "Default threshold produced no output"
    assert result_aggressive.stdout.strip(), "Aggressive threshold produced no output"

    # Test with very high threshold (should skip most/all audio)
    cmd_high = [
        sys.executable,
        "-m",
        "vosk_wrapper_1000.main",
        "transcribe-file",
        str(TRANSCRIPT_AUDIO),
        "--model",
        "vosk-model-en-gb-0.1",
        "--silence-threshold",
        "10000.0",
    ]

    result_high = subprocess.run(
        cmd_high,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    assert result_high.returncode == 0, f"High threshold failed: {result_high.stderr}"
    # With very high threshold, transcript should be empty
    assert "Total lines: 0" in result_high.stderr, (
        "High threshold should skip all audio"
    )


@pytest.mark.skipif(not TRANSCRIPT_AUDIO.exists(), reason="Test audio file not found")
def test_transcribe_file_with_noise_reduction(ensure_test_model_downloaded):
    """Test transcribe-file with noise reduction options."""
    # Test with noise reduction enabled (default)
    cmd_nr = [
        sys.executable,
        "-m",
        "vosk_wrapper_1000.main",
        "transcribe-file",
        str(TRANSCRIPT_AUDIO),
        "--model",
        TEST_MODEL,
        "--noise-reduction-level",
        "0.1",
    ]

    result_nr = subprocess.run(
        cmd_nr,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    assert result_nr.returncode == 0, f"Noise reduction failed: {result_nr.stderr}"

    # Test with noise reduction disabled
    cmd_no_nr = [
        sys.executable,
        "-m",
        "vosk_wrapper_1000.main",
        "transcribe-file",
        str(TRANSCRIPT_AUDIO),
        "--model",
        TEST_MODEL,
        "--disable-noise-reduction",
    ]

    result_no_nr = subprocess.run(
        cmd_no_nr,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    assert result_no_nr.returncode == 0, (
        f"No noise reduction failed: {result_no_nr.stderr}"
    )

    # Both should produce output (transcripts go to stdout)
    assert result_nr.stdout.strip(), "Noise reduction enabled produced no output"
    assert result_no_nr.stdout.strip(), "Noise reduction disabled produced no output"


@pytest.mark.skipif(not TRANSCRIPT_AUDIO.exists(), reason="Test audio file not found")
def test_transcribe_file_silence_threshold_variations(ensure_test_model_downloaded):
    """Test transcribe-file with different silence threshold values to reduce choppiness."""
    # Read expected transcript
    with open(EXPECTED_TRANSCRIPT) as f:
        expected_text = f.read().strip()

    thresholds = [10.0, 25.0, 50.0, 75.0]
    results = {}

    for threshold in thresholds:
        cmd = [
            sys.executable,
            "-m",
            "vosk_wrapper_1000.main",
            "transcribe-file",
            str(TRANSCRIPT_AUDIO),
            "--model",
            TEST_MODEL,
            "--silence-threshold",
            str(threshold),
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )

        assert result.returncode == 0, (
            f"Silence threshold {threshold} failed: {result.stderr}"
        )

        # Extract transcript from stdout
        stdout_lines = [
            line for line in result.stdout.strip().split("\n") if line.strip()
        ]
        actual_transcript = stdout_lines[0].strip() if stdout_lines else ""

        # Validate transcription quality
        expected_words = set(expected_text.lower().split())
        actual_words = set(actual_transcript.lower().split())
        common_words = expected_words & actual_words
        word_match_ratio = (
            len(common_words) / len(expected_words) if expected_words else 0
        )

        # Ensure reasonable transcription quality (at least 70% word match for parameter testing)
        assert word_match_ratio >= 0.7, (
            f"Silence threshold {threshold}: Poor transcription quality. "
            f"Expected: '{expected_text}', Got: '{actual_transcript}' (match ratio: {word_match_ratio:.2%})"
        )

        results[threshold] = actual_transcript

        # Each threshold should produce some output
        assert results[threshold], f"Silence threshold {threshold} produced no output"


@pytest.mark.skipif(not TRANSCRIPT_AUDIO.exists(), reason="Test audio file not found")
def test_transcribe_file_vad_hysteresis_variations(ensure_test_model_downloaded):
    """Test transcribe-file with different VAD hysteresis values to reduce choppiness."""
    # Read expected transcript
    with open(EXPECTED_TRANSCRIPT) as f:
        expected_text = f.read().strip()

    hysteresis_values = [5, 10, 15, 20]
    results = {}

    for hysteresis in hysteresis_values:
        cmd = [
            sys.executable,
            "-m",
            "vosk_wrapper_1000.main",
            "transcribe-file",
            str(TRANSCRIPT_AUDIO),
            "--model",
            TEST_MODEL,
            "--vad-hysteresis",
            str(hysteresis),
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )

        assert result.returncode == 0, (
            f"VAD hysteresis {hysteresis} failed: {result.stderr}"
        )

        # Extract transcript from stdout
        stdout_lines = [
            line for line in result.stdout.strip().split("\n") if line.strip()
        ]
        actual_transcript = stdout_lines[0].strip() if stdout_lines else ""

        # Validate transcription quality
        expected_words = set(expected_text.lower().split())
        actual_words = set(actual_transcript.lower().split())
        common_words = expected_words & actual_words
        word_match_ratio = (
            len(common_words) / len(expected_words) if expected_words else 0
        )

        # Ensure reasonable transcription quality (at least 70% word match for parameter testing)
        assert word_match_ratio >= 0.7, (
            f"VAD hysteresis {hysteresis}: Poor transcription quality. "
            f"Expected: '{expected_text}', Got: '{actual_transcript}' (match ratio: {word_match_ratio:.2%})"
        )

        results[hysteresis] = actual_transcript

        # Each hysteresis value should produce some output
        assert results[hysteresis], f"VAD hysteresis {hysteresis} produced no output"


@pytest.mark.skipif(not TRANSCRIPT_AUDIO.exists(), reason="Test audio file not found")
def test_transcribe_file_pre_roll_duration_variations(ensure_test_model_downloaded):
    """Test transcribe-file with different pre-roll duration values to reduce choppiness."""
    # Read expected transcript
    with open(EXPECTED_TRANSCRIPT) as f:
        expected_text = f.read().strip()

    durations = [0.5, 1.0, 2.0, 3.0]
    results = {}

    for duration in durations:
        cmd = [
            sys.executable,
            "-m",
            "vosk_wrapper_1000.main",
            "transcribe-file",
            str(TRANSCRIPT_AUDIO),
            "--model",
            TEST_MODEL,
            "--pre-roll-duration",
            str(duration),
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )

        assert result.returncode == 0, (
            f"Pre-roll duration {duration} failed: {result.stderr}"
        )

        # Extract transcript from stdout
        stdout_lines = [
            line for line in result.stdout.strip().split("\n") if line.strip()
        ]
        actual_transcript = stdout_lines[0].strip() if stdout_lines else ""

        # Validate transcription quality
        expected_words = set(expected_text.lower().split())
        actual_words = set(actual_transcript.lower().split())
        common_words = expected_words & actual_words
        word_match_ratio = (
            len(common_words) / len(expected_words) if expected_words else 0
        )

        # Ensure reasonable transcription quality (at least 70% word match for parameter testing)
        assert word_match_ratio >= 0.7, (
            f"Pre-roll duration {duration}: Poor transcription quality. "
            f"Expected: '{expected_text}', Got: '{actual_transcript}' (match ratio: {word_match_ratio:.2%})"
        )

        results[duration] = actual_transcript

        # Each duration should produce some output
        assert results[duration], f"Pre-roll duration {duration} produced no output"


@pytest.mark.skipif(not TRANSCRIPT_AUDIO.exists(), reason="Test audio file not found")
def test_transcribe_file_noise_reduction_level_variations(ensure_test_model_downloaded):
    """Test transcribe-file with different noise reduction levels to reduce choppiness."""
    # Read expected transcript
    with open(EXPECTED_TRANSCRIPT) as f:
        expected_text = f.read().strip()

    levels = [0.01, 0.05, 0.1, 0.2]
    results = {}

    for level in levels:
        cmd = [
            sys.executable,
            "-m",
            "vosk_wrapper_1000.main",
            "transcribe-file",
            str(TRANSCRIPT_AUDIO),
            "--model",
            TEST_MODEL,
            "--noise-reduction-level",
            str(level),
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )

        assert result.returncode == 0, (
            f"Noise reduction level {level} failed: {result.stderr}"
        )

        # Extract transcript from stdout
        stdout_lines = [
            line for line in result.stdout.strip().split("\n") if line.strip()
        ]
        actual_transcript = stdout_lines[0].strip() if stdout_lines else ""

        # Validate transcription quality
        expected_words = set(expected_text.lower().split())
        actual_words = set(actual_transcript.lower().split())
        common_words = expected_words & actual_words
        word_match_ratio = (
            len(common_words) / len(expected_words) if expected_words else 0
        )

        # Ensure reasonable transcription quality (at least 70% word match for parameter testing)
        assert word_match_ratio >= 0.7, (
            f"Noise reduction level {level}: Poor transcription quality. "
            f"Expected: '{expected_text}', Got: '{actual_transcript}' (match ratio: {word_match_ratio:.2%})"
        )

        results[level] = actual_transcript

        # Each level should produce some output
        assert results[level], f"Noise reduction level {level} produced no output"


@pytest.mark.skipif(not TRANSCRIPT_AUDIO.exists(), reason="Test audio file not found")
def test_transcribe_file_with_record_audio(ensure_test_model_downloaded, tmp_path):
    """Test transcribe-file with --record-audio to capture processed audio for analysis."""

    # Create a temporary file for recorded audio
    record_file = tmp_path / "recorded_audio.wav"

    cmd = [
        sys.executable,
        "-m",
        "vosk_wrapper_1000.main",
        "transcribe-file",
        str(TRANSCRIPT_AUDIO),
        "--model",
        TEST_MODEL,
        "--record-audio",
        str(record_file),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    assert result.returncode == 0, f"Record audio failed: {result.stderr}"

    # Check that transcript was produced
    transcript = result.stdout.strip()
    assert transcript, "No transcript produced with record-audio"

    # Check that the recorded audio file was created
    assert record_file.exists(), "Recorded audio file was not created"

    # Check that the file has some size (not empty)
    assert record_file.stat().st_size > 0, "Recorded audio file is empty"


@pytest.mark.skipif(not TRANSCRIPT_AUDIO.exists(), reason="Test audio file not found")
def test_transcribe_file_combined_anti_choppiness_config(
    ensure_test_model_downloaded, tmp_path
):
    """Test transcribe-file with combined configuration optimized to reduce choppiness."""

    # Configuration optimized for reducing choppiness:
    # - Lower silence threshold (more sensitive to quiet speech)
    # - Higher VAD hysteresis (less likely to cut off speech prematurely)
    # - Longer pre-roll (more context before speech detection)
    # - Lighter noise reduction (less aggressive processing)
    record_file = tmp_path / "anti_choppy_audio.wav"

    cmd = [
        sys.executable,
        "-m",
        "vosk_wrapper_1000.main",
        "transcribe-file",
        str(TRANSCRIPT_AUDIO),
        "--model",
        TEST_MODEL,
        "--silence-threshold",
        "25.0",  # Lower threshold for more sensitivity
        "--vad-hysteresis",
        "15",  # Higher hysteresis to prevent premature speech cutoff
        "--pre-roll-duration",
        "1.5",  # Moderate pre-roll duration
        "--noise-reduction-level",
        "0.02",  # Lighter noise reduction
        "--record-audio",
        str(record_file),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    assert result.returncode == 0, f"Anti-choppiness config failed: {result.stderr}"

    # Read expected transcript
    with open(EXPECTED_TRANSCRIPT) as f:
        expected_text = f.read().strip()

    # Extract transcript from stdout
    stdout_lines = [line for line in result.stdout.strip().split("\n") if line.strip()]
    actual_transcript = stdout_lines[0].strip() if stdout_lines else ""

    # Validate transcription quality - should maintain good accuracy with anti-choppiness settings
    expected_words = set(expected_text.lower().split())
    actual_words = set(actual_transcript.lower().split())
    common_words = expected_words & actual_words
    word_match_ratio = len(common_words) / len(expected_words) if expected_words else 0

    # Ensure good transcription quality (at least 75% word match for optimized config)
    assert word_match_ratio >= 0.75, (
        f"Anti-choppiness config: Poor transcription quality. "
        f"Expected: '{expected_text}', Got: '{actual_transcript}' (match ratio: {word_match_ratio:.2%})"
    )

    # Check that the recorded audio file was created and has content
    assert record_file.exists(), "Anti-choppiness recorded audio file was not created"
    assert record_file.stat().st_size > 0, (
        "Anti-choppiness recorded audio file is empty"
    )


# Tests for transcript_test_2 (audio with background noise)


@pytest.mark.skipif(
    not TRANSCRIPT_AUDIO_2.exists(), reason="Test audio file 2 not found"
)
@pytest.mark.skipif(
    not EXPECTED_TRANSCRIPT_2.exists(), reason="Expected transcript file 2 not found"
)
def test_transcribe_file_e2e_test2(ensure_test_model_downloaded):
    """Test the transcribe-file command end-to-end with audio containing background noise."""
    # Read expected transcript
    with open(EXPECTED_TRANSCRIPT_2) as f:
        expected_text = f.read().strip()

    # Run transcribe-file command
    cmd = [
        sys.executable,
        "-m",
        "vosk_wrapper_1000.main",
        "transcribe-file",
        str(TRANSCRIPT_AUDIO_2),
        "--model",
        TEST_MODEL,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    # Check that command succeeded
    assert result.returncode == 0, f"Command failed: {result.stderr}"

    # The transcript is printed to stdout (first line), while logging goes to stderr
    # Extract just the first line from stdout which contains the transcript
    stdout_lines = [line for line in result.stdout.strip().split("\n") if line.strip()]

    # The first non-empty line should be the transcript
    actual_transcript = stdout_lines[0].strip() if stdout_lines else ""

    # Compare with expected (allowing for minor differences in transcription)
    # The model might produce slightly different results, so we check for key words
    expected_words = set(expected_text.lower().split())
    actual_words = set(actual_transcript.lower().split())

    # Check that most words match (at least 70% overlap for noisy audio)
    common_words = expected_words & actual_words
    word_match_ratio = len(common_words) / len(expected_words) if expected_words else 0

    assert word_match_ratio >= 0.7, (
        f"Transcript mismatch. Expected: '{expected_text}', "
        f"Got: '{actual_transcript}' (match ratio: {word_match_ratio:.2%})"
    )


@pytest.mark.skipif(
    not TRANSCRIPT_AUDIO_2.exists(), reason="Test audio file 2 not found"
)
def test_transcribe_file_test2_with_noise_reduction(ensure_test_model_downloaded):
    """Test transcribe-file with noise reduction on audio containing background noise."""
    # Read expected transcript
    with open(EXPECTED_TRANSCRIPT_2) as f:
        expected_text = f.read().strip()

    # Test with noise reduction enabled (should improve results on noisy audio)
    cmd_nr = [
        sys.executable,
        "-m",
        "vosk_wrapper_1000.main",
        "transcribe-file",
        str(TRANSCRIPT_AUDIO_2),
        "--model",
        TEST_MODEL,
        "--noise-reduction-level",
        "0.1",  # Moderate noise reduction for background noise
    ]

    result_nr = subprocess.run(
        cmd_nr,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    assert result_nr.returncode == 0, f"Noise reduction failed: {result_nr.stderr}"

    # Extract transcript
    stdout_lines = [
        line for line in result_nr.stdout.strip().split("\n") if line.strip()
    ]
    actual_transcript = stdout_lines[0].strip() if stdout_lines else ""

    # Validate transcription quality
    expected_words = set(expected_text.lower().split())
    actual_words = set(actual_transcript.lower().split())
    common_words = expected_words & actual_words
    word_match_ratio = len(common_words) / len(expected_words) if expected_words else 0

    # Should maintain reasonable accuracy with noise reduction
    assert word_match_ratio >= 0.6, (
        f"Noise reduction on noisy audio: Poor transcription quality. "
        f"Expected: '{expected_text}', Got: '{actual_transcript}' (match ratio: {word_match_ratio:.2%})"
    )

    # Test with noise reduction disabled for comparison
    cmd_no_nr = [
        sys.executable,
        "-m",
        "vosk_wrapper_1000.main",
        "transcribe-file",
        str(TRANSCRIPT_AUDIO_2),
        "--model",
        TEST_MODEL,
        "--disable-noise-reduction",
    ]

    result_no_nr = subprocess.run(
        cmd_no_nr,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    assert result_no_nr.returncode == 0, (
        f"No noise reduction failed: {result_no_nr.stderr}"
    )

    # Both should produce output
    assert actual_transcript, "Noise reduction enabled produced no output"
    assert result_no_nr.stdout.strip(), "Noise reduction disabled produced no output"


@pytest.mark.skipif(
    not TRANSCRIPT_AUDIO_2.exists(), reason="Test audio file 2 not found"
)
def test_transcribe_file_test2_aggressive_noise_reduction(ensure_test_model_downloaded):
    """Test aggressive noise reduction settings on audio with background noise."""
    # Read expected transcript
    with open(EXPECTED_TRANSCRIPT_2) as f:
        expected_text = f.read().strip()

    # Test with aggressive noise reduction (higher level)
    cmd_aggressive = [
        sys.executable,
        "-m",
        "vosk_wrapper_1000.main",
        "transcribe-file",
        str(TRANSCRIPT_AUDIO_2),
        "--model",
        TEST_MODEL,
        "--noise-reduction-level",
        "0.3",  # Aggressive noise reduction
        "--noise-reduction-min-rms-ratio",
        "0.3",  # Allow more aggressive processing
    ]

    result_aggressive = subprocess.run(
        cmd_aggressive,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    assert result_aggressive.returncode == 0, (
        f"Aggressive noise reduction failed: {result_aggressive.stderr}"
    )

    # Extract transcript
    stdout_lines = [
        line for line in result_aggressive.stdout.strip().split("\n") if line.strip()
    ]
    actual_transcript = stdout_lines[0].strip() if stdout_lines else ""

    # Should still produce some output (may be degraded but shouldn't be empty)
    assert actual_transcript, "Aggressive noise reduction produced no output"

    # Validate that it doesn't completely destroy the audio
    expected_words = set(expected_text.lower().split())
    actual_words = set(actual_transcript.lower().split())
    common_words = expected_words & actual_words
    word_match_ratio = len(common_words) / len(expected_words) if expected_words else 0

    # Even with aggressive settings, should maintain some intelligibility
    assert word_match_ratio >= 0.4, (
        f"Aggressive noise reduction: Too much audio degradation. "
        f"Expected: '{expected_text}', Got: '{actual_transcript}' (match ratio: {word_match_ratio:.2%})"
    )


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
