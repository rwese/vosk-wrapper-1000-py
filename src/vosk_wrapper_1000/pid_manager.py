"""PID management for vosk-wrapper-1000 instances."""

import os
import sys

from .xdg_paths import APP_NAME, get_xdg_cache_home


def get_pid_dir():
    """Get the directory for storing PID files."""
    pid_dir = get_xdg_cache_home() / APP_NAME / "pids"
    pid_dir.mkdir(parents=True, exist_ok=True)
    return pid_dir


def get_pid_file(name="default"):
    """Get the PID file path for a named instance."""
    pid_dir = get_pid_dir()
    return pid_dir / f"{name}.pid"


def write_pid(name="default"):
    """Write the current process PID to a file."""
    pid_file = get_pid_file(name)
    pid = os.getpid()

    # Check if another instance is already running
    if pid_file.exists():
        try:
            old_pid = int(pid_file.read_text().strip())
            # Check if process is actually running
            os.kill(old_pid, 0)  # This raises OSError if process doesn't exist
            print(
                f"Error: Instance '{name}' is already running with PID {old_pid}",
                file=sys.stderr,
            )
            print(f"If this is incorrect, remove: {pid_file}", file=sys.stderr)
            sys.exit(1)
        except (OSError, ValueError):
            # Process doesn't exist or PID file is corrupted, safe to overwrite
            pass

    pid_file.write_text(str(pid))
    return pid


def remove_pid(name="default"):
    """Remove the PID file for a named instance."""
    pid_file = get_pid_file(name)
    if pid_file.exists():
        pid_file.unlink()


def read_pid(name="default"):
    """Read the PID for a named instance."""
    pid_file = get_pid_file(name)
    if not pid_file.exists():
        return None

    try:
        pid = int(pid_file.read_text().strip())
        # Verify process exists
        os.kill(pid, 0)
        return pid
    except (OSError, ValueError):
        # Process doesn't exist or PID file is corrupted
        return None


def list_instances():
    """List all running instances."""
    pid_dir = get_pid_dir()
    instances = []

    for pid_file in pid_dir.glob("*.pid"):
        name = pid_file.stem
        try:
            pid = int(pid_file.read_text().strip())
            # Check if process is running
            os.kill(pid, 0)
            instances.append((name, pid))
        except (OSError, ValueError):
            # Clean up stale PID file
            pid_file.unlink()

    return instances


def send_signal_to_instance(name, sig):
    """Send a signal to a named instance."""
    pid = read_pid(name)
    if pid is None:
        print(f"Error: No running instance found with name '{name}'", file=sys.stderr)
        print("Use 'vosk-wrapper-1000 list' to see running instances", file=sys.stderr)
        return False

    try:
        os.kill(pid, sig)
        return True
    except OSError as e:
        print(
            f"Error sending signal to instance '{name}' (PID {pid}): {e}",
            file=sys.stderr,
        )
        return False
