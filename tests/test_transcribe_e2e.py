#!/usr/bin/env python3
"""End-to-end test for transcribe-file command with real audio assets."""

import os
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


@pytest.mark.skipif(not TRANSCRIPT_AUDIO.exists(), reason="Test audio file not found")
@pytest.mark.skipif(
    not EXPECTED_TRANSCRIPT.exists(), reason="Expected transcript file not found"
)
def test_transcribe_file_e2e(ensure_test_model_downloaded):
    """Test the transcribe-file command end-to-end with real audio."""
    # Read expected transcript
    with open(EXPECTED_TRANSCRIPT, "r") as f:
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
        "vosk-model-en-gb-0.1",
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
        "vosk-model-en-gb-0.1",
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


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
