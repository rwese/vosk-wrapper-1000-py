"""Shared pytest fixtures for vosk-wrapper-1000 tests."""

import pytest

# Test model used across all e2e tests
TEST_MODEL = "vosk-model-en-gb-0.1"


@pytest.fixture(scope="session")
def ensure_test_model_downloaded():
    """Ensure the test model is downloaded before running any tests.

    This is a session-scoped fixture that runs once at the beginning of the test session.
    It downloads the test model if it's not already present.
    """
    from vosk_core.xdg_paths import get_models_dir
    from vosk_wrapper_1000.download_model import download_model, fetch_models

    models_dir = get_models_dir()
    model_path = models_dir / TEST_MODEL

    if not model_path.exists():
        print(f"\nDownloading test model {TEST_MODEL}...")
        models = fetch_models()
        result = download_model(TEST_MODEL, str(models_dir), models)
        if result is None:
            pytest.skip(f"Failed to download test model {TEST_MODEL}")
        print(f"Test model {TEST_MODEL} downloaded successfully")
    else:
        print(f"\nTest model {TEST_MODEL} already available")

    return model_path
