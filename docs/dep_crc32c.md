# google-crc32c Dependency Configuration

## Overview

The `google-crc32c` package is a transitive dependency (via `aiortc`) that provides fast CRC32C checksum calculations. It has both a pure Python implementation and a much faster C extension that links against the `libcrc32c` library.

## The Problem

When running the application, you may encounter this warning:

```
/path/to/google_crc32c/__init__.py:29: RuntimeWarning: As the c extension couldn't be imported,
`google-crc32c` is using a pure python implementation that is significantly slower.
If possible, please configure a c build environment and compile the extension
```

## Root Cause

This warning appears when:

1. **No pre-built wheels available**: Python 3.14 is very new, and `google-crc32c` doesn't have pre-compiled binary wheels for it yet
2. **Missing C library**: The package attempts to build from source but fails because the `crc32c` C library headers are not available
3. **Fallback behavior**: When the C extension build fails, the package silently falls back to a pure Python implementation

The pure Python implementation is **significantly slower** than the C extension, which can impact WebRTC performance where checksums are calculated frequently.

## Solution

### 1. Install the crc32c Library

First, install the system-level `crc32c` library that provides the C implementation:

```bash
brew install crc32c
```

This installs:
- Header files to `/home/linuxbrew/.linuxbrew/include/crc32c/`
- Library files to `/home/linuxbrew/.linuxbrew/lib/`

### 2. Rebuild google-crc32c with C Extension

Set the compiler flags to find the library and rebuild:

```bash
export CFLAGS="-I/home/linuxbrew/.linuxbrew/include"
export LDFLAGS="-L/home/linuxbrew/.linuxbrew/lib"
uv pip install --force-reinstall --no-binary google-crc32c google-crc32c
```

The `--no-binary` flag forces building from source instead of using pre-built wheels.

### 3. Verify the Installation

Confirm the C extension loaded successfully:

```bash
python -c "import google_crc32c._crc32c; print('C extension loaded successfully')"
```

If no warnings appear, the C extension is working correctly.

## Why This Matters

### Performance Impact

The pure Python implementation is orders of magnitude slower than the C extension:

- **C extension**: Native code, optimized for performance
- **Pure Python**: Interpreted code with significant overhead

For WebRTC applications (like our browser-based speech recognition server), CRC32C checksums are calculated for:
- SRTP/SRTCP packet integrity
- Data channel message verification
- Stream encryption verification

Slow checksums can cause:
- Increased CPU usage
- Higher latency in real-time communication
- Potential packet drops due to processing delays

### When You Need This

You need to follow these steps if:

1. You're using Python 3.14 (or any newer Python version before official wheels are available)
2. You're on a system without pre-built wheels (some ARM platforms, non-standard Linux distributions)
3. You're building in a containerized environment without the C library

## Troubleshooting

### Build fails with "crc32c/crc32c.h: No such file or directory"

The `crc32c` library isn't installed. Run `brew install crc32c` first.

### Warning still appears after rebuild

The C extension may not have been copied to the correct location. Check if the `.so` file exists:

```bash
python -c "import google_crc32c; import os; print(os.path.dirname(google_crc32c.__file__))"
ls -la $(python -c "import google_crc32c; import os; print(os.path.dirname(google_crc32c.__file__))")/*.so
```

You should see `_crc32c.cpython-314-x86_64-linux-gnu.so` (or similar).

### Warning appears when using `uv tool run` or installed UV tools

If you installed this package as a UV tool (e.g., `uv tool install vosk-wrapper-1000`), it has its own isolated Python environment separate from your project's `.venv`. You need to apply the fix to both locations.

**Option 1: Manually copy the compiled extension**

First, build the extension as described above in a temporary location:

```bash
cd /tmp
curl -L https://files.pythonhosted.org/packages/source/g/google-crc32c/google_crc32c-1.7.1.tar.gz -o google_crc32c.tar.gz
tar -xzf google_crc32c.tar.gz
cd google_crc32c-1.7.1
export CFLAGS="-I/home/linuxbrew/.linuxbrew/include"
export LDFLAGS="-L/home/linuxbrew/.linuxbrew/lib"
python setup.py build
```

Then copy the built extension to the UV tool's environment:

```bash
# Find the UV tool's site-packages directory
TOOL_PATH=$(find ~/.local/share/uv/tools/vosk-wrapper-1000*/lib/python*/site-packages/google_crc32c -type d 2>/dev/null | head -1)

# Copy the compiled extension
cp /tmp/google_crc32c-1.7.1/build/lib.*/google_crc32c/_crc32c.*.so "$TOOL_PATH/"
```

**Option 2: Reinstall the tool after fixing the system**

After installing `crc32c` via Homebrew and setting up the build environment, reinstall the tool:

```bash
uv tool uninstall vosk-wrapper-1000
export CFLAGS="-I/home/linuxbrew/.linuxbrew/include"
export LDFLAGS="-L/home/linuxbrew/.linuxbrew/lib"
uv tool install vosk-wrapper-1000
```

Note: This may not work reliably with UV's caching, so Option 1 is recommended.

### Using system package manager instead of Homebrew

On Fedora/RHEL:
```bash
sudo dnf install crc32c-devel
```

On Ubuntu/Debian:
```bash
sudo apt-get install libcrc32c-dev
```

Then rebuild with standard system paths:
```bash
uv pip install --force-reinstall --no-binary google-crc32c google-crc32c
```

## Future Considerations

Once `google-crc32c` publishes official wheels for Python 3.14, this manual process won't be necessary. The package will install with the C extension automatically.

Check for available wheels at: https://pypi.org/project/google-crc32c/#files
