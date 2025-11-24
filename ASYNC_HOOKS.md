# Async Hook Support

The HookManager now supports both synchronous and asynchronous hook execution.

## Features

- **Async mode (default)**: Hooks run in background threads without blocking the main application
- **Sync mode**: Original behavior where hooks run sequentially and block
- **Callback support**: Get notified of hook return codes in async mode
- **Thread tracking**: Monitor running hooks and wait for completion

## Usage

### Basic Async Execution (Default)

```python
from vosk_wrapper_1000.hook_manager import HookManager

hook_manager = HookManager("hooks")

# Run hooks asynchronously (non-blocking)
hook_manager.run_hooks("line", payload="transcript text", async_mode=True)
```

### Synchronous Execution (Original Behavior)

```python
# Run hooks synchronously (blocking)
action = hook_manager.run_hooks("line", payload="transcript text", async_mode=False)

# action codes:
# 0 = Continue
# 100 = Stop Listening
# 101 = Terminate Application
# 102 = Abort
```

### Using Callbacks

```python
def handle_hook_result(return_code):
    if return_code == 100:
        print("Hook requested stop listening")
    elif return_code == 101:
        print("Hook requested termination")

hook_manager.run_hooks(
    "start",
    async_mode=True,
    callback=handle_hook_result
)
```

### Monitoring and Waiting

```python
# Check how many hooks are running
count = hook_manager.get_running_hooks_count()
print(f"{count} hooks are currently running")

# Wait for all hooks to complete (with timeout)
completed = hook_manager.wait_for_hooks(timeout=5.0)
if completed:
    print("All hooks completed")
else:
    print("Timeout waiting for hooks")
```

## Migration Guide

### Backward Compatibility

The default behavior has changed to async mode. To maintain the original synchronous behavior:

**Before:**
```python
hook_manager.run_hooks("line", payload=text)
```

**After (maintain sync behavior):**
```python
hook_manager.run_hooks("line", payload=text, async_mode=False)
```

**After (use new async behavior):**
```python
hook_manager.run_hooks("line", payload=text, async_mode=True)
# or just:
hook_manager.run_hooks("line", payload=text)  # async_mode=True is default
```

### Return Code Handling

In **async mode**, return codes from hooks don't affect the flow immediately. Instead:
- Use callbacks to handle return codes
- The `run_hooks()` method always returns 0 in async mode

In **sync mode**, return codes work as before:
- Return codes determine application flow
- Higher priority codes (101, 102) cause immediate return

## Performance

Async mode provides significant performance benefits when:
- Running multiple hooks
- Hooks perform I/O operations (network, file system)
- Hooks have variable execution times

**Example timing:**
- Sync mode with 2 hooks (2s each): ~2 seconds total
- Async mode with 2 hooks (2s each): ~0 seconds (non-blocking)

## Thread Safety

- Each hook runs in its own daemon thread
- Threads are automatically cleaned up after completion
- Thread-safe tracking of running hooks using locks
- Safe to call from the main thread

## Testing

See `test_hook_async.py` for comprehensive test examples covering:
- Async vs sync execution timing
- Callback functionality
- Return code handling
- Hook completion waiting
