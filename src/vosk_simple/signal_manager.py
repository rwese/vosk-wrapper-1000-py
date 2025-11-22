"""Signal handling utilities for vosk-wrapper-1000."""

import signal
import sys


class SignalManager:
    """Manages signal handling for daemon lifecycle."""

    def __init__(self):
        self.running = True
        self.listening = False
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup signal handlers for daemon control."""
        signal.signal(signal.SIGUSR1, self._handle_start)
        signal.signal(signal.SIGUSR2, self._handle_stop)
        signal.signal(signal.SIGINT, self._handle_terminate)
        signal.signal(signal.SIGTERM, self._handle_terminate)

    def _handle_start(self, sig, frame):
        """Handle SIGUSR1 - start listening."""
        print("Received SIGUSR1: Starting listening...", file=sys.stderr)
        self.listening = True

    def _handle_stop(self, sig, frame):
        """Handle SIGUSR2 - stop listening."""
        print("Received SIGUSR2: Stopping listening...", file=sys.stderr)
        self.listening = False

    def _handle_terminate(self, sig, frame):
        """Handle SIGINT/SIGTERM - terminate daemon."""
        print(f"Received signal {sig}: Terminating...", file=sys.stderr)
        self.running = False
        self.listening = False

    def is_running(self) -> bool:
        """Check if daemon should continue running."""
        return self.running

    def is_listening(self) -> bool:
        """Check if daemon should be listening."""
        return self.listening

    def set_listening(self, listening: bool):
        """Set listening state."""
        self.listening = listening

    def set_running(self, running: bool):
        """Set running state."""
        self.running = running
