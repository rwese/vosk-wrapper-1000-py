"""IPC Server for vosk-wrapper-1000.

Provides Unix domain socket-based IPC for command & control and
real-time transcription streaming.

Protocol: Line-delimited JSON (see docs/IPC_PROTOCOL.md)
"""

import json
import logging
import os
import select
import socket
import time
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

logger = logging.getLogger(__name__)


class IPCClient:
    """Represents a connected IPC client."""

    def __init__(self, sock: socket.socket, addr: str):
        self.sock = sock
        self.addr = addr
        self.buffer = ""
        self.subscribed = False
        self.subscribed_events: Set[str] = set()
        self.connected_at = time.time()

    def fileno(self):
        """Return socket file descriptor for select()."""
        return self.sock.fileno()


class IPCServer:
    """Non-blocking Unix domain socket server for IPC.

    Integrates into the main event loop without threading.
    Handles multiple concurrent clients with subscription-based event broadcasting.
    """

    def __init__(self, socket_path: str, send_partials: bool = True):
        """Initialize IPC server.

        Args:
            socket_path: Path to Unix domain socket
            send_partials: Whether to broadcast partial transcription results
        """
        self.socket_path = socket_path
        self.send_partials = send_partials
        self.server_sock: Optional[socket.socket] = None
        self.clients: List[IPCClient] = []
        self.session_id = str(uuid4())
        self.started_at = time.time()

    def start(self) -> bool:
        """Start listening on Unix domain socket.

        Returns:
            True if started successfully, False otherwise
        """
        # Remove stale socket file
        if os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except OSError as e:
                logger.error(f"Failed to remove stale socket {self.socket_path}: {e}")
                return False

        # Create socket directory if needed
        socket_dir = os.path.dirname(self.socket_path)
        if socket_dir:
            os.makedirs(socket_dir, exist_ok=True)

        try:
            # Create Unix domain socket
            self.server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.server_sock.bind(self.socket_path)
            self.server_sock.listen(5)
            self.server_sock.setblocking(False)

            logger.info(f"IPC server listening on {self.socket_path}")
            return True

        except OSError as e:
            logger.error(f"Failed to start IPC server: {e}")
            return False

    def stop(self):
        """Stop IPC server and clean up resources."""
        # Close all client connections
        for client in self.clients[:]:
            self._close_client(client)

        # Close server socket
        if self.server_sock:
            self.server_sock.close()
            self.server_sock = None

        # Remove socket file
        if os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except OSError:
                pass

        logger.info("IPC server stopped")

    def process(self, timeout: float = 0.0) -> List[Dict[str, Any]]:
        """Process pending connections and messages (non-blocking).

        Should be called regularly from main event loop.

        Args:
            timeout: Max time to wait for I/O (0 = non-blocking)

        Returns:
            List of command messages received from clients
        """
        if not self.server_sock:
            return []

        commands = []

        # Build list of sockets to monitor
        readable_sockets = [self.server_sock] + [c.sock for c in self.clients]

        try:
            # Non-blocking select
            readable, _, exceptional = select.select(
                readable_sockets, [], readable_sockets, timeout
            )

            # Accept new connections
            if self.server_sock in readable:
                self._accept_connection()

            # Read from clients
            for client in self.clients[:]:
                if client.sock in readable:
                    messages = self._read_client(client)
                    for msg in messages:
                        if msg.get("type") == "command":
                            commands.append({"client": client, "message": msg})
                        else:
                            # Unknown message type, send error
                            self._send_error(
                                client,
                                msg.get("id"),
                                "INVALID_MESSAGE",
                                "Unknown message type",
                            )

                # Close clients with errors
                if client.sock in exceptional:
                    self._close_client(client)

        except Exception as e:
            logger.error(f"Error in IPC server process: {e}")

        return commands

    def send_response(
        self,
        client: IPCClient,
        request_id: Optional[str],
        success: bool,
        data: Optional[Dict] = None,
        error: Optional[Dict] = None,
    ):
        """Send response to a specific client.

        Args:
            client: Client to send to
            request_id: ID from the request (for matching)
            success: Whether request succeeded
            data: Response data (if success=True)
            error: Error details (if success=False)
        """
        response: Dict[str, Any] = {
            "id": request_id,
            "type": "response",
            "success": success,
        }

        if success:
            response["data"] = data or {}
        else:
            response["error"] = error or {
                "code": "UNKNOWN_ERROR",
                "message": "Unknown error",
            }

        self._send_to_client(client, response)

    def broadcast_event(self, event: Dict[str, Any], event_type: Optional[str] = None):
        """Broadcast event to all subscribed clients.

        Args:
            event: Event data (must include "type" field)
            event_type: Event type filter (if None, send to all subscribed clients)
        """
        if "type" not in event:
            logger.error("Attempted to broadcast event without 'type' field")
            return

        evt_type = event_type or event["type"]

        for client in self.clients[:]:
            # Send to subscribed clients
            if client.subscribed:
                # Check if client subscribed to this specific event type
                if not client.subscribed_events or evt_type in client.subscribed_events:
                    self._send_to_client(client, event)

    def _accept_connection(self):
        """Accept a new client connection."""
        try:
            if self.server_sock is None:
                return
            client_sock, addr = self.server_sock.accept()
            client_sock.setblocking(False)

            client = IPCClient(client_sock, str(addr))
            self.clients.append(client)

            logger.debug(f"IPC client connected: {addr}")

        except OSError as e:
            logger.error(f"Error accepting connection: {e}")

    def _read_client(self, client: IPCClient) -> List[Dict[str, Any]]:
        """Read and parse messages from client.

        Args:
            client: Client to read from

        Returns:
            List of parsed JSON messages
        """
        messages: List[Dict[str, Any]] = []

        try:
            data = client.sock.recv(4096).decode("utf-8")

            if not data:
                # Client disconnected
                self._close_client(client)
                return messages

            # Append to buffer
            client.buffer += data

            # Process complete lines
            while "\n" in client.buffer:
                line, client.buffer = client.buffer.split("\n", 1)
                line = line.strip()

                if not line:
                    continue

                try:
                    msg = json.loads(line)
                    messages.append(msg)
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON from client: {e}")
                    self._send_error(client, None, "INVALID_JSON", str(e))

        except OSError as e:
            logger.error(f"Error reading from client: {e}")
            self._close_client(client)

        return messages

    def _send_to_client(self, client: IPCClient, message: Dict[str, Any]):
        """Send JSON message to client.

        Args:
            client: Client to send to
            message: Message to send (will be JSON-encoded)
        """
        try:
            data = json.dumps(message) + "\n"
            client.sock.sendall(data.encode("utf-8"))

        except OSError as e:
            logger.error(f"Error sending to client: {e}")
            self._close_client(client)

    def _send_error(
        self, client: IPCClient, request_id: Optional[str], code: str, message: str
    ):
        """Send error response to client.

        Args:
            client: Client to send to
            request_id: Request ID (or None)
            code: Error code
            message: Error message
        """
        self.send_response(
            client, request_id, success=False, error={"code": code, "message": message}
        )

    def _close_client(self, client: IPCClient):
        """Close client connection and remove from list.

        Args:
            client: Client to close
        """
        try:
            client.sock.close()
        except OSError:
            pass

        if client in self.clients:
            self.clients.remove(client)
            logger.debug(f"IPC client disconnected: {client.addr}")

    def get_client_count(self) -> int:
        """Get number of connected clients."""
        return len(self.clients)

    def has_subscribers(self) -> bool:
        """Check if any clients are subscribed to events."""
        return any(c.subscribed for c in self.clients)
