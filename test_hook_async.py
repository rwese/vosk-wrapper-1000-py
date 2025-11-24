#!/usr/bin/env python3
"""Test async hook functionality."""

import os
import sys
import tempfile
import time
import stat
from pathlib import Path
import importlib.util

# Import hook_manager directly without triggering __init__.py
hook_manager_path = os.path.join(os.path.dirname(__file__), 'src', 'vosk_wrapper_1000', 'hook_manager.py')
spec = importlib.util.spec_from_file_location("hook_manager", hook_manager_path)
hook_manager_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook_manager_module)
HookManager = hook_manager_module.HookManager


def test_async_hooks():
    """Test that hooks run asynchronously."""

    # Create temporary hooks directory
    with tempfile.TemporaryDirectory() as tmpdir:
        hooks_dir = Path(tmpdir)
        line_dir = hooks_dir / "line"
        line_dir.mkdir()

        # Create a slow hook that takes 2 seconds
        slow_hook = line_dir / "01_slow.sh"
        slow_hook.write_text("""#!/bin/bash
sleep 2
echo "Slow hook completed"
exit 0
""")
        slow_hook.chmod(slow_hook.stat().st_mode | stat.S_IEXEC)

        # Create a fast hook
        fast_hook = line_dir / "02_fast.sh"
        fast_hook.write_text("""#!/bin/bash
echo "Fast hook completed"
exit 0
""")
        fast_hook.chmod(fast_hook.stat().st_mode | stat.S_IEXEC)

        # Test async execution
        print("Testing async hook execution...")
        hook_manager = HookManager(str(hooks_dir))

        start_time = time.time()
        hook_manager.run_hooks("line", payload="test", async_mode=True)
        elapsed_time = time.time() - start_time

        # In async mode, should return immediately (< 0.5 seconds)
        print(f"Async execution took {elapsed_time:.2f} seconds")
        assert elapsed_time < 0.5, f"Async execution took too long: {elapsed_time:.2f}s"

        # Verify hooks are running
        time.sleep(0.1)  # Give threads time to start
        running_count = hook_manager.get_running_hooks_count()
        print(f"Running hooks count: {running_count}")
        assert running_count > 0, "No hooks are running"

        # Wait for all hooks to complete
        print("Waiting for hooks to complete...")
        completed = hook_manager.wait_for_hooks(timeout=5.0)
        assert completed, "Hooks did not complete in time"

        print("✓ Async hooks test passed!")

        # Test sync execution for comparison
        print("\nTesting sync hook execution...")
        start_time = time.time()
        hook_manager.run_hooks("line", payload="test", async_mode=False)
        elapsed_time = time.time() - start_time

        # In sync mode, should wait for all hooks (> 2 seconds)
        print(f"Sync execution took {elapsed_time:.2f} seconds")
        assert elapsed_time >= 2.0, f"Sync execution was too fast: {elapsed_time:.2f}s"

        print("✓ Sync hooks test passed!")


def test_hook_callback():
    """Test hook callback functionality."""

    with tempfile.TemporaryDirectory() as tmpdir:
        hooks_dir = Path(tmpdir)
        start_dir = hooks_dir / "start"
        start_dir.mkdir()

        # Create hooks with different return codes
        hook1 = start_dir / "01_success.sh"
        hook1.write_text("""#!/bin/bash
echo "Hook 1"
exit 0
""")
        hook1.chmod(hook1.stat().st_mode | stat.S_IEXEC)

        hook2 = start_dir / "02_stop.sh"
        hook2.write_text("""#!/bin/bash
echo "Hook 2 - requesting stop"
exit 100
""")
        hook2.chmod(hook2.stat().st_mode | stat.S_IEXEC)

        # Track return codes
        return_codes = []

        def callback(code):
            return_codes.append(code)

        # Run hooks with callback
        print("\nTesting hook callbacks...")
        hook_manager = HookManager(str(hooks_dir))
        hook_manager.run_hooks("start", async_mode=True, callback=callback)

        # Wait for completion
        hook_manager.wait_for_hooks(timeout=5.0)

        # Verify we received the return codes
        print(f"Return codes received: {return_codes}")
        assert len(return_codes) == 2, f"Expected 2 return codes, got {len(return_codes)}"
        assert 0 in return_codes, "Expected return code 0"
        assert 100 in return_codes, "Expected return code 100"

        print("✓ Hook callback test passed!")


if __name__ == "__main__":
    test_async_hooks()
    test_hook_callback()
    print("\n✓ All tests passed!")
