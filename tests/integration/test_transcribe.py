"""
Integration tests for file transcription functionality.
"""

import unittest


class TestFileTranscription(unittest.TestCase):
    """Test file transcription functionality."""

    def test_transcribe_file_imports(self):
        """Test that transcribe_file function can be imported."""
        # This test ensures the function exists and can be imported
        from vosk_transcribe import transcribe_file

        self.assertTrue(callable(transcribe_file))

    def test_transcribe_main_function(self):
        """Test that main function can be imported."""
        from vosk_transcribe import main

        self.assertTrue(callable(main))


if __name__ == "__main__":
    unittest.main()
