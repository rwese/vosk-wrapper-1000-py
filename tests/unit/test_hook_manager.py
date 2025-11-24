"""
Unit tests for hook manager functionality.
"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vosk_wrapper_1000.hook_manager import HookManager


class TestHookManager(unittest.TestCase):
    """Test hook manager functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.hooks_dir = Path(self.temp_dir) / "hooks"
        self.hooks_dir.mkdir()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def _create_test_hook(self, name, content):
        """Create a test hook script."""
        hook_dir = self.hooks_dir / name
        hook_dir.mkdir(exist_ok=True)
        hook_path = hook_dir / "01_test.sh"
        hook_path.write_text(content)
        hook_path.chmod(0o755)
        return hook_path

    def test_hook_execution_with_empty_payload(self):
        """Test that hooks receive empty payload correctly."""
        # Create a hook that reads stdin and writes to a file
        output_file = Path(self.temp_dir) / "hook_output.txt"
        hook_content = f"""#!/bin/bash
input=$(cat)
echo "RECEIVED: '$input'" > {output_file}
"""
        self._create_test_hook("test", hook_content)

        hm = HookManager(str(self.hooks_dir))

        result = hm.run_hooks("test", payload="", async_mode=False)

        # Check that the hook was executed successfully
        self.assertEqual(result, 0)

        # Verify the hook received the empty payload
        self.assertTrue(output_file.exists())
        content = output_file.read_text().strip()
        self.assertEqual(content, "RECEIVED: ''")

    def test_hook_execution_with_data_payload(self):
        """Test that hooks receive data payload correctly."""
        output_file = Path(self.temp_dir) / "hook_output_data.txt"
        hook_content = f"""#!/bin/bash
input=$(cat)
echo "RECEIVED: '$input'" > {output_file}
"""
        self._create_test_hook("test", hook_content)

        hm = HookManager(str(self.hooks_dir))

        result = hm.run_hooks("test", payload="hello world", async_mode=False)

        self.assertEqual(result, 0)
        self.assertTrue(output_file.exists())
        content = output_file.read_text().strip()
        self.assertEqual(content, "RECEIVED: 'hello world'")

    def test_hook_execution_with_none_payload(self):
        """Test that hooks work when no payload is provided."""
        output_file = Path(self.temp_dir) / "hook_output_none.txt"
        hook_content = f"""#!/bin/bash
# Try to read stdin - should get EOF immediately
input=$(cat)
echo "RECEIVED: '$input'" > {output_file}
"""
        self._create_test_hook("test", hook_content)

        hm = HookManager(str(self.hooks_dir))

        result = hm.run_hooks("test", payload=None, async_mode=False)

        self.assertEqual(result, 0)
        self.assertTrue(output_file.exists())
        content = output_file.read_text().strip()
        self.assertEqual(content, "RECEIVED: ''")

    def test_hook_execution_async_with_empty_payload(self):
        """Test that async hooks receive empty payload correctly."""
        output_file = Path(self.temp_dir) / "hook_output_async_empty.txt"
        hook_content = f"""#!/bin/bash
input=$(cat)
echo "RECEIVED: '$input'" > {output_file}
"""
        self._create_test_hook("test", hook_content)

        hm = HookManager(str(self.hooks_dir))

        result = hm.run_hooks("test", payload="", async_mode=True)

        # Wait for async hooks to complete
        self.assertTrue(hm.wait_for_hooks(timeout=5.0))

        self.assertEqual(result, 0)
        self.assertTrue(output_file.exists())
        content = output_file.read_text().strip()
        self.assertEqual(content, "RECEIVED: ''")

    def test_hook_execution_async_with_data_payload(self):
        """Test that async hooks receive data payload correctly."""
        output_file = Path(self.temp_dir) / "hook_output_async_data.txt"
        hook_content = f"""#!/bin/bash
input=$(cat)
echo "RECEIVED: '$input'" > {output_file}
"""
        self._create_test_hook("test", hook_content)

        hm = HookManager(str(self.hooks_dir))

        result = hm.run_hooks("test", payload="async data", async_mode=True)

        self.assertTrue(hm.wait_for_hooks(timeout=5.0))

        self.assertEqual(result, 0)
        self.assertTrue(output_file.exists())
        content = output_file.read_text().strip()
        self.assertEqual(content, "RECEIVED: 'async data'")

    def test_hook_return_codes(self):
        """Test that hook return codes are handled correctly."""
        # Create hooks with different return codes
        hook_content_100 = """#!/bin/bash
exit 100
"""
        hook_content_101 = """#!/bin/bash
exit 101
"""
        hook_content_102 = """#!/bin/bash
exit 102
"""

        self._create_test_hook("stop", hook_content_100)
        self._create_test_hook("terminate", hook_content_101)
        self._create_test_hook("abort", hook_content_102)

        hm = HookManager(str(self.hooks_dir))

        # Test stop hook (return code 100)
        result = hm.run_hooks("stop", async_mode=False)
        self.assertEqual(result, 100)

        # Test terminate hook (return code 101)
        result = hm.run_hooks("terminate", async_mode=False)
        self.assertEqual(result, 101)

        # Test abort hook (return code 102)
        result = hm.run_hooks("abort", async_mode=False)
        self.assertEqual(result, 102)


if __name__ == "__main__":
    unittest.main()
