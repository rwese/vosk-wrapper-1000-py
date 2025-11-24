"""WebRTC server for vosk-wrapper-1000.

Provides WebRTC signaling and peer connection handling for browser-based
speech recognition clients.

Uses aiortc for WebRTC functionality and integrates with the existing
audio processing pipeline.
"""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, Optional

import numpy as np
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from aiortc.contrib.media import MediaRecorder
from av import AudioFrame

logger = logging.getLogger(__name__)


class AudioSink:
    """Receives audio from WebRTC track and forwards to audio callback."""

    def __init__(self, track: MediaStreamTrack, audio_callback, peer_id: str):
        """Initialize audio sink.

        Args:
            track: WebRTC audio track
            audio_callback: Function to call with audio data (bytes, sample_rate, channels)
            peer_id: Unique identifier for this peer connection
        """
        self.track = track
        self.audio_callback = audio_callback
        self.peer_id = peer_id
        self.task = None

    async def start(self):
        """Start receiving audio frames."""
        self.task = asyncio.create_task(self._receive_audio())

    async def stop(self):
        """Stop receiving audio frames."""
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

    async def _receive_audio(self):
        """Receive and process audio frames from WebRTC track."""
        try:
            while True:
                try:
                    frame = await self.track.recv()

                    # Convert audio frame to bytes
                    if isinstance(frame, AudioFrame):
                        # Get audio data as numpy array
                        audio_array = frame.to_ndarray()

                        # Convert to int16 PCM format expected by audio processor
                        if audio_array.dtype == np.float32:
                            # Convert float32 [-1.0, 1.0] to int16 [-32768, 32767]
                            audio_array = (audio_array * 32767).astype(np.int16)
                        elif audio_array.dtype != np.int16:
                            audio_array = audio_array.astype(np.int16)

                        # Convert to bytes
                        audio_bytes = audio_array.tobytes()

                        # Forward to audio callback with metadata
                        if self.audio_callback:
                            await asyncio.to_thread(
                                self.audio_callback,
                                audio_bytes,
                                frame.sample_rate,
                                len(frame.layout.channels),
                                self.peer_id
                            )

                except Exception as e:
                    logger.error(f"Error receiving audio frame: {e}")
                    break

        except asyncio.CancelledError:
            logger.debug(f"Audio sink for peer {self.peer_id} cancelled")
        except Exception as e:
            logger.error(f"Audio sink error for peer {self.peer_id}: {e}")


class WebRTCPeer:
    """Represents a single WebRTC peer connection."""

    def __init__(self, peer_id: str, audio_callback):
        """Initialize WebRTC peer.

        Args:
            peer_id: Unique identifier for this peer
            audio_callback: Function to call with audio data
        """
        self.peer_id = peer_id
        self.audio_callback = audio_callback
        self.pc = RTCPeerConnection()
        self.audio_sink: Optional[AudioSink] = None

        # Track connection state
        @self.pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(f"Peer {peer_id} connection state: {self.pc.connectionState}")
            if self.pc.connectionState == "failed":
                await self.close()

        # Handle incoming audio tracks
        @self.pc.on("track")
        async def on_track(track):
            logger.info(f"Peer {peer_id} received {track.kind} track")
            if track.kind == "audio":
                self.audio_sink = AudioSink(track, audio_callback, peer_id)
                await self.audio_sink.start()

    async def create_offer(self) -> Dict[str, str]:
        """Create WebRTC offer.

        Returns:
            Dictionary with SDP offer
        """
        offer = await self.pc.createOffer()
        await self.pc.setLocalDescription(offer)

        return {
            "type": offer.type,
            "sdp": offer.sdp
        }

    async def set_answer(self, answer_sdp: str):
        """Set remote answer.

        Args:
            answer_sdp: SDP answer from client
        """
        answer = RTCSessionDescription(sdp=answer_sdp, type="answer")
        await self.pc.setRemoteDescription(answer)

    async def close(self):
        """Close peer connection and cleanup."""
        if self.audio_sink:
            await self.audio_sink.stop()
        await self.pc.close()


class WebRTCServer:
    """WebRTC signaling server for browser-based speech recognition."""

    def __init__(self, config: Dict[str, Any], audio_callback):
        """Initialize WebRTC server.

        Args:
            config: WebRTC configuration
            audio_callback: Function to call with audio data from WebRTC streams
                          Should accept (audio_bytes, sample_rate, channels, peer_id)
        """
        self.config = config
        self.audio_callback = audio_callback
        self.running = False
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self.peers: Dict[str, WebRTCPeer] = {}
        self._server_task: Optional[asyncio.Task] = None

    async def _handle_offer(self, request: web.Request) -> web.Response:
        """Handle WebRTC offer request from client.

        Creates a new peer connection and returns an offer.
        """
        try:
            # Generate unique peer ID
            peer_id = str(uuid.uuid4())

            # Create new peer connection
            peer = WebRTCPeer(peer_id, self.audio_callback)
            self.peers[peer_id] = peer

            # Create offer
            offer = await peer.create_offer()

            logger.info(f"Created offer for peer {peer_id}")

            return web.json_response({
                "peer_id": peer_id,
                "sdp": offer["sdp"],
                "type": offer["type"]
            })

        except Exception as e:
            logger.error(f"Error handling offer: {e}")
            return web.json_response(
                {"error": str(e)},
                status=500
            )

    async def _handle_answer(self, request: web.Request) -> web.Response:
        """Handle WebRTC answer from client.

        Sets the remote description on the peer connection.
        """
        try:
            peer_id = request.match_info["peer_id"]

            # Get peer connection
            peer = self.peers.get(peer_id)
            if not peer:
                return web.json_response(
                    {"error": "Peer not found"},
                    status=404
                )

            # Parse answer
            data = await request.json()
            answer_sdp = data.get("sdp")

            if not answer_sdp:
                return web.json_response(
                    {"error": "Missing SDP in answer"},
                    status=400
                )

            # Set answer
            await peer.set_answer(answer_sdp)

            logger.info(f"Set answer for peer {peer_id}")

            return web.json_response({"status": "ok"})

        except Exception as e:
            logger.error(f"Error handling answer: {e}")
            return web.json_response(
                {"error": str(e)},
                status=500
            )

    async def _handle_delete_peer(self, request: web.Request) -> web.Response:
        """Handle peer disconnection request."""
        try:
            peer_id = request.match_info["peer_id"]

            peer = self.peers.get(peer_id)
            if peer:
                await peer.close()
                del self.peers[peer_id]
                logger.info(f"Deleted peer {peer_id}")

            return web.json_response({"status": "ok"})

        except Exception as e:
            logger.error(f"Error deleting peer: {e}")
            return web.json_response(
                {"error": str(e)},
                status=500
            )

    async def _handle_status(self, request: web.Request) -> web.Response:
        """Handle status request."""
        return web.json_response({
            "running": self.running,
            "active_connections": len(self.peers),
            "peers": list(self.peers.keys())
        })

    async def _start_server(self):
        """Start the aiohttp server."""
        try:
            # Create aiohttp application
            self.app = web.Application()

            # Add routes
            self.app.router.add_post("/offer", self._handle_offer)
            self.app.router.add_post("/answer/{peer_id}", self._handle_answer)
            self.app.router.add_delete("/peer/{peer_id}", self._handle_delete_peer)
            self.app.router.add_get("/status", self._handle_status)

            # Start server
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()

            host = self.config.get("host", "0.0.0.0")
            port = self.config.get("port", 8080)

            self.site = web.TCPSite(self.runner, host, port)
            await self.site.start()

            self.running = True
            logger.info(f"WebRTC server started on {host}:{port}")

            # Keep server running
            while self.running:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"WebRTC server error: {e}")
            self.running = False
        finally:
            await self._cleanup()

    async def _cleanup(self):
        """Cleanup server resources."""
        # Close all peer connections
        for peer in list(self.peers.values()):
            await peer.close()
        self.peers.clear()

        # Cleanup aiohttp
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()

    def start(self) -> bool:
        """Start the WebRTC server.

        Returns:
            True if started successfully, False otherwise
        """
        try:
            # Get or create event loop
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No event loop running, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Create and run server task
            self._server_task = loop.create_task(self._start_server())

            logger.info(
                f"WebRTC server starting on {self.config['host']}:{self.config['port']}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to start WebRTC server: {e}")
            return False

    def stop(self):
        """Stop the WebRTC server."""
        self.running = False

        if self._server_task:
            self._server_task.cancel()

        logger.info("WebRTC server stopped")

    def get_status(self) -> Dict[str, Any]:
        """Get server status."""
        return {
            "running": self.running,
            "host": self.config.get("host", "unknown"),
            "port": self.config.get("port", 8080),
            "active_connections": len(self.peers),
            "max_connections": self.config.get("max_connections", 5),
            "total_peers": len(self.peers),
            "peer_ids": list(self.peers.keys()),
        }
