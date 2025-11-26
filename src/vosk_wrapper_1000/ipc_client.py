"""IPC Client for vosk-wrapper-1000.

Provides client library for connecting to the daemon via Unix domain socket.
"""

import json
import logging
import socket
import time
from collections.abc import Callable
from typing import Any, cast
from uuid import uuid4

logger = logging.getLogger(__name__)


class IPCError(Exception):
    """Base exception for IPC errors."""

    pass


class ConnectionError(IPCError):
    """Raised when connection to server fails."""

    pass


class TimeoutError(IPCError):
    """Raised when request times out."""

    pass


class CommandError(IPCError):
    """Raised when server returns an error response."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class IPCClient:
    """Client for communicating with vosk-wrapper daemon via IPC.

    Example:
        client = IPCClient("/tmp/vosk-wrapper-default.sock")
        client.connect()

        # Send command
        status = client.send_command("status")
        print(f"Listening: {status['listening']}")

        # Stream events
        for event in client.stream_events():
            if event['type'] == 'transcription':
                print(event['text'])

        client.disconnect()
    """

    def __init__(self, socket_path: str, timeout: float = 5.0):
        """Initialize IPC client.

        Args:
            socket_path: Path to Unix domain socket
            timeout: Default timeout for requests in seconds
        """
        self.socket_path = socket_path
        self.timeout = timeout
        self.sock: socket.socket | None = None
        self.buffer = ""
        self._connected = False

    def connect(self):
        """Connect to IPC server.

        Raises:
            ConnectionError: If connection fails
        """
        try:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            self.sock.connect(self.socket_path)
            self._connected = True
            logger.debug(f"Connected to IPC server at {self.socket_path}")

        except OSError as e:
            raise ConnectionError(
                f"Failed to connect to {self.socket_path}: {e}"
            ) from e

    def disconnect(self):
        """Disconnect from IPC server."""
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None
            self._connected = False
            logger.debug("Disconnected from IPC server")

    def is_connected(self) -> bool:
        """Check if connected to server."""
        return self._connected

    def send_command(
        self,
        command: str,
        params: dict | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Send command to server and wait for response.

        Args:
            command: Command name (e.g., "start", "stop", "status")
            params: Command parameters
            timeout: Request timeout (uses default if None)

        Returns:
            Response data dict

        Raises:
            ConnectionError: If not connected
            TimeoutError: If request times out
            CommandError: If server returns error
        """
        if not self._connected:
            raise ConnectionError("Not connected to server")

        # Generate request
        request_id = str(uuid4())
        request = {
            "id": request_id,
            "type": "command",
            "command": command,
            "params": params or {},
        }

        # Send request
        self._send_message(request)

        # Wait for response
        response = self._wait_for_response(request_id, timeout or self.timeout)

        # Check for errors
        if not response.get("success", False):
            error = response.get("error", {})
            raise CommandError(
                error.get("code", "UNKNOWN_ERROR"),
                error.get("message", "Unknown error"),
            )

        return cast(dict[str, Any], response.get("data", {}))

    def subscribe(self, events: list[str] | None = None):
        """Subscribe to event stream.

        Args:
            events: List of event types to subscribe to (None = all events)

        Raises:
            ConnectionError: If not connected
            CommandError: If subscription fails
        """
        params = {}
        if events:
            params["events"] = events

        self.send_command("subscribe", params)
        logger.debug(f"Subscribed to events: {events or 'all'}")

    def unsubscribe(self):
        """Unsubscribe from event stream.

        Raises:
            ConnectionError: If not connected
            CommandError: If unsubscribe fails
        """
        self.send_command("unsubscribe")
        logger.debug("Unsubscribed from events")

    def stream_events(self, callback: Callable[[dict], bool] | None = None):
        """Stream events from server (blocking).

        Yields events indefinitely until connection closes or callback returns False.

        Args:
            callback: Optional callback function called for each event.
                     If returns False, streaming stops.

        Yields:
            Event dictionaries

        Raises:
            ConnectionError: If not connected
        """
        if not self._connected:
            raise ConnectionError("Not connected to server")

        # Set to blocking mode for streaming
        if self.sock:
            self.sock.settimeout(None)

        try:
            while True:
                message = self._read_message()
                if not message:
                    break

                # Skip response messages (only yield events)
                if message.get("type") == "response":
                    continue

                # Yield event
                if callback:
                    if not callback(message):
                        break
                else:
                    yield message

        except KeyboardInterrupt:
            logger.debug("Event streaming interrupted")
        except OSError as e:
            logger.error(f"Error streaming events: {e}")
            raise ConnectionError(f"Connection lost: {e}") from e
        finally:
            # Restore timeout
            if self.sock:
                self.sock.settimeout(self.timeout)

    def _send_message(self, message: dict[str, Any]):
        """Send JSON message to server.

        Args:
            message: Message dict to send

        Raises:
            ConnectionError: If send fails
        """
        try:
            data = json.dumps(message) + "\n"
            if self.sock is None:
                raise ConnectionError("Socket is not connected")
            self.sock.sendall(data.encode("utf-8"))
        except OSError as e:
            raise ConnectionError(f"Failed to send message: {e}") from e

    def _read_message(self) -> dict[str, Any] | None:
        """Read one complete JSON message from server.

        Returns:
            Parsed message dict or None if connection closed

        Raises:
            ConnectionError: If read fails
        """
        try:
            # Read until we have a complete line
            while "\n" not in self.buffer:
                if self.sock is None:
                    raise ConnectionError("Socket is not connected")
                data = self.sock.recv(4096).decode("utf-8")
                if not data:
                    return None  # Connection closed
                self.buffer += data

            # Extract one line
            line, self.buffer = self.buffer.split("\n", 1)
            line = line.strip()

            if not line:
                return self._read_message()  # Skip empty lines

            # Parse JSON
            try:
                parsed = json.loads(line)
                if isinstance(parsed, dict):
                    return parsed
                logger.warning(f"Received non-dict message: {parsed}")
                return self._read_message()
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON received: {e}")
                return self._read_message()  # Skip invalid messages

        except OSError as e:
            raise ConnectionError(f"Failed to read message: {e}") from e

    def _wait_for_response(self, request_id: str, timeout: float) -> dict[str, Any]:
        """Wait for response message with matching ID.

        Args:
            request_id: Request ID to match
            timeout: Timeout in seconds

        Returns:
            Response message

        Raises:
            TimeoutError: If timeout expires
            ConnectionError: If connection fails
        """
        start_time = time.time()

        # Set socket timeout
        if self.sock:
            self.sock.settimeout(timeout)

        try:
            while True:
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    raise TimeoutError(f"Request timed out after {timeout}s")

                # Read message
                message = self._read_message()
                if not message:
                    raise ConnectionError(
                        "Connection closed while waiting for response"
                    )

                # Check if it's our response
                if (
                    message.get("type") == "response"
                    and message.get("id") == request_id
                ):
                    return message

                # Not our response, keep waiting
                # (could be event or response for different request)

        finally:
            # Restore default timeout
            if self.sock:
                self.sock.settimeout(self.timeout)

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


def get_socket_path(instance_name: str) -> str:
    """Get socket path for instance.

    Args:
        instance_name: Instance name

    Returns:
        Path to Unix domain socket
    """
    # Try to read from config file first
    try:
        from .config_manager import ConfigManager

        config_manager = ConfigManager()
        config = config_manager.load_config()
        return config.ipc.socket_path.format(instance_name=instance_name)
    except Exception:
        # Fallback: Try systemd RuntimeDirectory location first, then /tmp
        import os

        uid = os.getuid()

        # Systemd RuntimeDirectory: /run/user/UID/vosk-wrapper-1000/
        systemd_socket = f"/run/user/{uid}/vosk-wrapper-1000/{instance_name}.sock"
        if os.path.exists(systemd_socket):
            return systemd_socket

        # Legacy /run/user/UID location
        legacy_socket = f"/run/user/{uid}/vosk-wrapper-{instance_name}.sock"
        if os.path.exists(legacy_socket):
            return legacy_socket

        # Fallback to /tmp for non-systemd environments
        return f"/tmp/vosk-wrapper-{instance_name}.sock"
