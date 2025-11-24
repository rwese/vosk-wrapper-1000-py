"""Main daemon service for vosk-wrapper-1000."""

import argparse
import json
import logging
import os
import queue
import signal
import sys
import time
from typing import List
from uuid import uuid4

# Import local modules
from vosk_core.audio_processor import AudioProcessor
from vosk_core.audio_recorder import AudioRecorder
from vosk_core.audio_system import print_audio_system_info
from .config_manager import ConfigManager
from vosk_core.device_manager import DeviceManager
from .hook_manager import HookManager
from .ipc_server import IPCServer
from vosk_core.model_manager import ModelManager
from .pid_manager import remove_pid, send_signal_to_instance, write_pid
from .signal_manager import SignalManager
from vosk_core.xdg_paths import get_hooks_dir

try:
    from .webrtc_server import WebRTCServer

    WEBRTC_AVAILABLE = True
except ImportError:
    WEBRTC_AVAILABLE = False
    WebRTCServer = None

# Set up module logger
logger = logging.getLogger(__name__)


def setup_logging(log_level=None, config_manager=None):
    """Configure logging for the application.

    Args:
        log_level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                   If None, uses config file, then VOSK_LOG_LEVEL env var, defaults to WARNING
        config_manager: ConfigManager instance (optional, for loading from config file)
    """
    # Determine log level: CLI arg > env var > config file > default
    if log_level is None:
        log_level = os.environ.get("VOSK_LOG_LEVEL")
        if log_level is None and config_manager is not None:
            config = config_manager.load_config()
            log_level = config.logging.level
        if log_level is None:
            log_level = "WARNING"

    # Convert string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.WARNING)

    # Configure logging
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info(f"Logging configured with level: {log_level}")

    return log_level


def set_vosk_log_level(log_level: str):
    """Set Vosk log level based on our application log level.

    Args:
        log_level: Application log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    import vosk

    # Map our log levels to Vosk log levels
    # Vosk levels: -1 = silent, 0 = errors only, 1 = warnings, 2 = info (verbose)
    vosk_level_map = {
        "DEBUG": 2,  # Show all Vosk output including info
        "INFO": 2,  # Show all Vosk output including info
        "WARNING": 0,  # Show only Vosk errors
        "ERROR": 0,  # Show only Vosk errors
        "CRITICAL": -1,  # Silence Vosk completely
    }

    vosk_level = vosk_level_map.get(log_level.upper(), 0)
    vosk.SetLogLevel(vosk_level)
    logger.debug(f"Vosk log level set to {vosk_level} (app level: {log_level})")


def handle_ipc_command(
    cmd_data,
    ipc_server,
    signal_manager,
    device_manager,
    device_info,
    device_id,
    model_path,
    transcript_buffer,
    start_time,
    session_id,
    webrtc_server=None,
):
    """Handle IPC command from client.

    Args:
        cmd_data: Dict with 'client' and 'message' keys
        ipc_server: IPCServer instance
        signal_manager: SignalManager instance
        device_manager: DeviceManager instance
        device_info: Device info dict
        device_id: Device ID
        model_path: Path to model
        transcript_buffer: List of transcript lines
        start_time: Service start timestamp
        session_id: Current session ID

    Returns:
        None
    """
    client = cmd_data["client"]
    message = cmd_data["message"]
    command = message.get("command")
    request_id = message.get("id")

    try:
        if command == "start":
            if signal_manager.is_listening():
                ipc_server.send_response(
                    client,
                    request_id,
                    False,
                    error={"code": "ALREADY_LISTENING", "message": "Already listening"},
                )
            else:
                signal_manager.set_listening(True)
                ipc_server.send_response(
                    client, request_id, True, data={"listening": True}
                )

        elif command == "stop":
            if not signal_manager.is_listening():
                ipc_server.send_response(
                    client,
                    request_id,
                    False,
                    error={
                        "code": "NOT_LISTENING",
                        "message": "Not currently listening",
                    },
                )
            else:
                signal_manager.set_listening(False)
                ipc_server.send_response(
                    client, request_id, True, data={"listening": False}
                )

        elif command == "toggle":
            is_listening = signal_manager.is_listening()
            signal_manager.set_listening(not is_listening)
            ipc_server.send_response(
                client,
                request_id,
                True,
                data={
                    "listening": not is_listening,
                    "action": "started" if not is_listening else "stopped",
                },
            )

        elif command == "status":
            uptime = time.time() - start_time
            status_data = {
                "listening": signal_manager.is_listening(),
                "pid": os.getpid(),
                "uptime": uptime,
                "device": device_info["name"] if device_info else "default",
                "device_id": device_id,
                "model": str(model_path),
                "session_id": session_id,
            }
            ipc_server.send_response(client, request_id, True, data=status_data)

        elif command == "get_transcript":
            ipc_server.send_response(
                client,
                request_id,
                True,
                data={
                    "transcript": transcript_buffer,
                    "session_id": session_id,
                    "start_time": start_time,
                },
            )

        elif command == "get_devices":
            devices = device_manager.refresh_devices()
            device_list = [
                {
                    "id": d["id"],
                    "name": d["name"],
                    "channels": d["max_input_channels"],
                }
                for d in devices
            ]
            ipc_server.send_response(
                client,
                request_id,
                True,
                data={
                    "devices": device_list,
                    "current_device": device_id,
                },
            )

        elif command == "subscribe":
            client.subscribed = True
            events = message.get("params", {}).get("events", [])
            if events:
                client.subscribed_events = set(events)
            ipc_server.send_response(
                client, request_id, True, data={"subscribed": True}
            )

        elif command == "unsubscribe":
            client.subscribed = False
            client.subscribed_events = set()
            ipc_server.send_response(
                client, request_id, True, data={"subscribed": False}
            )

        elif command == "get_webrtc_status":
            if not WEBRTC_AVAILABLE:
                ipc_server.send_response(
                    client,
                    request_id,
                    False,
                    error={
                        "code": "WEBRTC_NOT_AVAILABLE",
                        "message": "WebRTC not available (aiortc not installed)",
                    },
                )
            elif webrtc_server:
                status = webrtc_server.get_status()
                ipc_server.send_response(client, request_id, True, data=status)
            else:
                ipc_server.send_response(
                    client,
                    request_id,
                    False,
                    error={
                        "code": "WEBRTC_NOT_ENABLED",
                        "message": "WebRTC server is not enabled",
                    },
                )

        elif command == "start_webrtc":
            if not WEBRTC_AVAILABLE:
                ipc_server.send_response(
                    client,
                    request_id,
                    False,
                    error={
                        "code": "WEBRTC_NOT_AVAILABLE",
                        "message": "WebRTC not available (aiortc not installed)",
                    },
                )
            elif webrtc_server:
                # WebRTC server is always "running" if enabled
                ipc_server.send_response(
                    client, request_id, True, data={"webrtc_running": True}
                )
            else:
                ipc_server.send_response(
                    client,
                    request_id,
                    False,
                    error={
                        "code": "WEBRTC_NOT_ENABLED",
                        "message": "WebRTC server is not enabled",
                    },
                )

        elif command == "stop_webrtc":
            if not WEBRTC_AVAILABLE:
                ipc_server.send_response(
                    client,
                    request_id,
                    False,
                    error={
                        "code": "WEBRTC_NOT_AVAILABLE",
                        "message": "WebRTC not available (aiortc not installed)",
                    },
                )
            elif webrtc_server:
                # Note: WebRTC server runs continuously, this just reports status
                ipc_server.send_response(
                    client, request_id, True, data={"webrtc_stopped": True}
                )
            else:
                ipc_server.send_response(
                    client,
                    request_id,
                    False,
                    error={
                        "code": "WEBRTC_NOT_ENABLED",
                        "message": "WebRTC server is not enabled",
                    },
                )

        else:
            ipc_server.send_response(
                client,
                request_id,
                False,
                error={
                    "code": "INVALID_COMMAND",
                    "message": f"Unknown command: {command}",
                },
            )

    except Exception as e:
        logger.error(f"Error handling IPC command '{command}': {e}")
        ipc_server.send_response(
            client,
            request_id,
            False,
            error={"code": "INTERNAL_ERROR", "message": str(e)},
        )


def run_service(args):
    """Run the main voice recognition service."""
    # Initialize config manager
    config_manager = ConfigManager()
    config = config_manager.load_config()

    # Override config with command line arguments
    if hasattr(args, "webrtc_enabled") and args.webrtc_enabled:
        config.webrtc.enabled = True
    if hasattr(args, "webrtc_port"):
        config.webrtc.port = args.webrtc_port
    if hasattr(args, "webrtc_host"):
        config.webrtc.host = args.webrtc_host

    # Initialize managers
    signal_manager = SignalManager()
    model_manager = ModelManager()
    device_manager = DeviceManager()
    hook_manager = HookManager(args.hooks_dir)

    # Resolve model path (support short names like "vosk-model-en-gb-0.1")
    try:
        resolved_model_path = model_manager.resolve_model_path(args.model)
        args.model = str(resolved_model_path)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Initialize IPC server if enabled
    ipc_server = None
    session_id = str(uuid4())
    start_time = time.time()

    if config.ipc.enabled:
        instance_name = args.name
        socket_path = config.ipc.socket_path.format(instance_name=instance_name)
        ipc_server = IPCServer(socket_path, send_partials=config.ipc.send_partials)
        if not ipc_server.start():
            logger.warning("Failed to start IPC server, continuing without IPC")
            ipc_server = None
        else:
            logger.info(f"IPC server started on {socket_path}")

    # Placeholder for WebRTC server (initialized later after audio_processor is created)
    webrtc_server = None
    webrtc_config = None
    if config.webrtc.enabled:
        if not WEBRTC_AVAILABLE:
            logger.warning(
                "WebRTC enabled but aiortc not available. Install with: pip install aiortc"
            )
        else:
            webrtc_config = {
                "host": config.webrtc.host,
                "port": config.webrtc.port,
                "stun_servers": config.webrtc.stun_servers,
                "turn_servers": config.webrtc.turn_servers,
                "max_connections": config.webrtc.max_connections,
                "audio_format": config.webrtc.audio_format,
                "sample_rate": config.webrtc.sample_rate,
                "channels": config.webrtc.channels,
            }
            logger.info("WebRTC will be initialized after audio processor setup")

    # Initialize audio components with placeholder rates
    audio_processor = AudioProcessor(
        device_rate=16000,  # Placeholder, will be updated after device detection
        model_rate=16000,  # Placeholder, will be updated after model loading
        noise_filter_enabled=not args.disable_noise_reduction,
        noise_reduction_strength=args.noise_reduction_level,
        stationary_noise=args.stationary_noise and not args.non_stationary_noise,
        silence_threshold=args.silence_threshold,
        normalize_audio=args.normalize_audio,
        normalization_target_level=args.normalize_target_level,
        vad_hysteresis_chunks=getattr(args, "vad_hysteresis", 10),
        noise_reduction_min_rms_ratio=getattr(
            args, "noise_reduction_min_rms_ratio", 0.5
        ),
        pre_roll_duration=getattr(args, "pre_roll_duration", 1.0),
    )

    audio_recorder = AudioRecorder(
        args.record_audio, 16000
    )  # Sample rate will be updated later

    # Handle --list-devices before fork (special case)
    if args.list_devices:
        device_manager.print_device_list()
        sys.exit(0)

    # Print audio system information
    print_audio_system_info()

    # Check if any audio devices are available
    available_devices = device_manager.refresh_devices()
    if not available_devices:
        logger.error("No audio input devices found on this system!")
        logger.error("Please check:")
        logger.error("  1. Microphone is connected and not muted")
        logger.error("  2. Microphone permissions are granted to Terminal/Python")
        logger.error("  3. No other application is using the microphone")
        logger.error("\nTo grant microphone permissions on macOS:")
        logger.error("  System Preferences → Security & Privacy → Privacy → Microphone")
        logger.error("  Enable Terminal (or your terminal application)")
        sys.exit(1)

    # Resolve device and get info
    device_info = device_manager.get_device_info(args.device)
    if device_info is None:
        device_id = None
        # Get default device sample rate
        import sounddevice as sd

        try:
            default_device = sd.query_devices(kind="input")
            device_samplerate = int(default_device["default_samplerate"])
        except (OSError, TypeError) as e:
            logger.error(f"Failed to query default input device: {e}")
            logger.error("No default input device available")
            sys.exit(1)
    else:
        device_id = device_info["id"]
        device_samplerate = int(device_info["default_samplerate"])

    # Validate device compatibility (only if device is specified)
    if device_id is not None:
        is_compatible, compatibility_msg = device_manager.validate_device_for_model(
            device_id, model_manager.get_model_sample_rate(args.model)
        )
        if not is_compatible:
            logger.error(f"Device compatibility error: {compatibility_msg}")
            logger.warning("Continuing despite device compatibility error...")
            # sys.exit(1)  # Temporarily disabled for debugging
        else:
            logger.info(f"Device compatibility: {compatibility_msg}")
    else:
        logger.info("Using default audio device")

    # Get model sample rate
    model_sample_rate = model_manager.get_model_sample_rate(args.model)

    # Update audio processor with rates
    if device_samplerate is not None:
        audio_processor.device_rate = device_samplerate
    audio_processor.model_rate = model_sample_rate

    # Initialize resampler now that we have the correct rates
    if audio_processor.device_rate != audio_processor.model_rate:
        import soxr

        audio_processor.soxr_resampler = soxr.ResampleStream(
            in_rate=audio_processor.device_rate,
            out_rate=audio_processor.model_rate,
            num_channels=1,
            quality="HQ",
        )
        logger.info(
            f"Initialized resampler: {audio_processor.device_rate} Hz → {audio_processor.model_rate} Hz"
        )

    # Setup audio recorder with model rate (record processed audio sent to Vosk)
    if args.record_audio:
        audio_recorder.sample_rate = model_sample_rate
        if not audio_recorder.start_recording():
            print(f"Error opening recording file {args.record_audio}", file=sys.stderr)
            sys.exit(1)
        print(
            f"Recording processed audio at {model_sample_rate} Hz to: {args.record_audio}",
            file=sys.stderr,
        )

    # Write PID file
    instance_name = args.name
    write_pid(instance_name)
    print(f"Instance '{instance_name}' starting...", file=sys.stderr)

    # Load Model
    print(f"Loading model from {args.model}...", file=sys.stderr)

    # Set Vosk log level to match application log level
    log_level = getattr(args, "_final_log_level", "WARNING")
    set_vosk_log_level(log_level)

    import vosk

    model = vosk.Model(str(args.model))
    print("Model loaded successfully", file=sys.stderr)

    # Create recognizer with optional grammar
    if args.grammar:
        print(f"Using grammar: {args.grammar}", file=sys.stderr)
        rec = vosk.KaldiRecognizer(model, model_sample_rate, args.grammar)
    else:
        rec = vosk.KaldiRecognizer(model, model_sample_rate)

    # Configure recognizer options
    if args.words:
        print("Enabling word-level timestamps", file=sys.stderr)
        rec.SetWords(True)

    if args.partial_words:
        print("Enabling partial word results", file=sys.stderr)
        rec.SetPartialWords(True)

    print("Recognizer created and configured", file=sys.stderr)

    # Setup signal handlers
    signal_manager._setup_handlers()
    print("Signal handlers setup", file=sys.stderr)

    logger.info(f"Service started. PID: {os.getpid()}")
    if device_info is not None:
        logger.info(f"Using audio device: {device_info['name']} (ID: {device_id})")
    else:
        logger.info("Using default audio device")
    logger.info("Send SIGUSR1 to start listening, SIGUSR2 to stop.")

    # Send ready event to IPC clients
    if ipc_server:
        ready_event = {
            "type": "ready",
            "pid": os.getpid(),
            "device": device_info["name"] if device_info else "default",
            "device_id": device_id,
            "model": str(args.model),
            "timestamp": time.time(),
        }
        ipc_server.broadcast_event(ready_event)
        logger.info("Service ready")

    # Initialize WebRTC server now that audio_processor is ready
    if webrtc_config is not None:
        try:
            # Placeholder for audio queue to be used by WebRTC callback
            webrtc_audio_queue: queue.Queue[tuple] = queue.Queue()

            # Create WebRTC audio callback that integrates with existing audio processing
            def webrtc_audio_callback(audio_bytes, sample_rate, channels, peer_id):
                """Handle audio from WebRTC streams."""
                try:
                    # Queue audio for processing (will be handled in main loop)
                    webrtc_audio_queue.put_nowait((audio_bytes, sample_rate, channels, peer_id))
                except queue.Full:
                    logger.warning(f"WebRTC audio queue full for peer {peer_id}, dropping audio")
                except Exception as e:
                    logger.error(f"Error queueing WebRTC audio: {e}")

            logger.info("Initializing WebRTC server...")
            webrtc_server = WebRTCServer(webrtc_config, webrtc_audio_callback)
            if not webrtc_server.start():
                logger.warning(
                    "Failed to start WebRTC server, continuing without WebRTC"
                )
                webrtc_server = None
            else:
                logger.info(
                    f"WebRTC server started on {webrtc_config['host']}:{webrtc_config['port']}"
                )
        except Exception as e:
            logger.error(f"Error initializing WebRTC server: {e}")
            logger.warning("Continuing without WebRTC")
            webrtc_server = None
    else:
        webrtc_audio_queue = None

    # Audio Stream Management
    stream = None
    audio_queue: queue.Queue[bytes] = queue.Queue()
    transcript_buffer: List[str] = []
    callback_counter = [0]  # Use list to allow modification in nested function

    # Special marker to indicate speech end
    SPEECH_END_MARKER = b"SPEECH_END"

    def audio_callback(indata, frames, time, status):
        """Audio callback for sounddevice."""
        if status:
            logger.warning(f"Audio callback status: {status}")

        if signal_manager.is_listening():
            try:
                # Debug: Check if we're actually getting audio when listening
                callback_counter[0] += 1
                if (
                    callback_counter[0] % 100 == 0
                ):  # Every ~100 callbacks (about 2 seconds at 1024 blocksize)
                    print(
                        f"DEBUG: Processing audio while listening - callback #{callback_counter[0]}, frames: {frames}, audio max: {indata.max():.6f}",
                        file=sys.stderr,
                    )

                # Process audio with VAD and pre-roll buffering
                # Returns empty list if silence, or list of chunks to process if speech detected
                audio_chunks = audio_processor.process_with_vad(indata)

                # Check if speech just ended
                if audio_processor.check_and_reset_speech_end():
                    # Put special marker to indicate speech end
                    try:
                        audio_queue.put_nowait(SPEECH_END_MARKER)
                    except queue.Full:
                        pass  # Skip if queue is full

                # Process each chunk returned (includes pre-roll audio when speech starts)
                for processed_audio in audio_chunks:
                    # Save to recording file if enabled (record exactly what goes to Vosk)
                    if args.record_audio:
                        audio_recorder.write_audio(processed_audio)

                    # Queue for Vosk processing
                    audio_queue.put_nowait(bytes(processed_audio))

            except queue.Full:
                # Drop audio frames if queue is full (prevents overflow)
                pass
            except Exception as e:
                logger.error(f"Error in audio callback: {e}")

    try:
        while signal_manager.is_running():
            # Process IPC commands (non-blocking)
            if ipc_server:
                commands = ipc_server.process(timeout=0.0)
                for cmd_data in commands:
                    handle_ipc_command(
                        cmd_data,
                        ipc_server,
                        signal_manager,
                        device_manager,
                        device_info,
                        device_id,
                        args.model,
                        transcript_buffer,
                        start_time,
                        session_id,
                        webrtc_server,
                    )

            # Process WebRTC audio (non-blocking)
            if webrtc_audio_queue is not None and signal_manager.is_listening():
                try:
                    while True:
                        audio_bytes, sample_rate, channels, peer_id = webrtc_audio_queue.get_nowait()
                        # Process WebRTC audio through the audio processor
                        audio_chunks = audio_processor.process_webrtc_audio(
                            audio_bytes, sample_rate, channels
                        )
                        # Queue processed audio chunks for recognition
                        for processed_audio in audio_chunks:
                            if args.record_audio:
                                audio_recorder.write_audio(processed_audio)
                            audio_queue.put_nowait(bytes(processed_audio))
                except queue.Empty:
                    pass  # No WebRTC audio to process
                except Exception as e:
                    logger.error(f"Error processing WebRTC audio in main loop: {e}")

            # Check if we need to start listening
            if signal_manager.is_listening() and stream is None:
                logger.info("Starting microphone stream...")
                logger.debug(
                    f"device_rate={audio_processor.device_rate}, device_id={device_id}"
                )

                try:
                    import sounddevice as sd  # Import here, in child process after fork

                    print(
                        f"DEBUG: About to create stream - device_id={device_id}, samplerate={audio_processor.device_rate}",
                        file=sys.stderr,
                    )

                    # Create stream using soxr-optimized callback
                    try:
                        stream = sd.InputStream(
                            samplerate=audio_processor.device_rate,
                            blocksize=1024,  # Smaller blocksize for better streaming
                            device=device_id,
                            dtype="int16",  # Use int16 to match audio processor expectations
                            channels=1,
                            callback=audio_callback,
                        )
                    except Exception as e:
                        print(
                            f"ERROR: Failed to create audio stream: {e}",
                            file=sys.stderr,
                        )
                        sys.exit(1)

                    print(
                        f"DEBUG: Stream created successfully - {stream}",
                        file=sys.stderr,
                    )

                    # Start the stream
                    stream.start()
                    print(
                        f"Microphone stream started at {audio_processor.device_rate} Hz (using soxr resampling to {audio_processor.model_rate} Hz).",
                        file=sys.stderr,
                    )
                    sys.stderr.flush()

                    # Broadcast status change event
                    if ipc_server:
                        ipc_server.broadcast_event(
                            {
                                "type": "status_change",
                                "event": "listening_started",
                                "timestamp": time.time(),
                            }
                        )

                    # Execute START hooks with async callback
                    def handle_start_hook_result(code):
                        if code == 100:
                            signal_manager.set_listening(False)
                        elif code == 101:
                            signal_manager.set_running(False)
                            signal_manager.set_listening(False)
                        elif code == 102:
                            signal_manager.set_running(False)
                            signal_manager.set_listening(False)

                    hook_manager.run_hooks(
                        "start", async_mode=True, callback=handle_start_hook_result
                    )

                except Exception as e:
                    print(f"Error starting stream: {e}", file=sys.stderr)
                    import traceback

                    traceback.print_exc(file=sys.stderr)
                    sys.stderr.flush()
                    signal_manager.set_listening(False)

            # Check if we need to stop listening
            if not signal_manager.is_listening() and stream is not None:
                print("Stopping microphone stream...", file=sys.stderr)
                stream.stop()
                stream.close()
                stream = None
                print("Microphone stream stopped.", file=sys.stderr)

                # Reset VAD state for next listening session
                audio_processor.reset_vad_state()

                # Broadcast status change event
                if ipc_server:
                    ipc_server.broadcast_event(
                        {
                            "type": "status_change",
                            "event": "listening_stopped",
                            "timestamp": time.time(),
                        }
                    )

                # Get final result from recognizer (any pending recognition)
                final_result = json.loads(rec.FinalResult())
                final_text = final_result.get("text", "")
                if final_text:
                    print(final_text)  # Output final recognition
                    sys.stdout.flush()
                    transcript_buffer.append(final_text)

                # Process accumulated transcript
                full_transcript = "\n".join(transcript_buffer)

                # Execute STOP hooks with async callback
                def handle_stop_hook_result(code):
                    if code == 101:
                        signal_manager.set_running(False)
                    elif code == 102:
                        signal_manager.set_running(False)
                        signal_manager.set_listening(False)

                hook_manager.run_hooks(
                    "stop",
                    payload=full_transcript,
                    async_mode=True,
                    callback=handle_stop_hook_result,
                )

                transcript_buffer = []  # Clear buffer
                rec.Reset()  # Reset recognizer for next session

            # Process audio if listening
            if signal_manager.is_listening() and stream is not None:
                try:
                    data = audio_queue.get(timeout=0.1)

                    # Check for speech end marker
                    if data == SPEECH_END_MARKER:
                        # Speech ended - finalize the current result
                        final_result = json.loads(rec.FinalResult())
                        final_text = final_result.get("text", "")
                        if final_text:
                            print(final_text)  # Output final recognition
                            sys.stdout.flush()
                            transcript_buffer.append(final_text)

                            # Broadcast final transcription to IPC clients
                            if ipc_server:
                                ipc_server.broadcast_event(
                                    {
                                        "type": "transcription",
                                        "result_type": "final",
                                        "text": final_text,
                                        "confidence": final_result.get(
                                            "confidence", 1.0
                                        ),
                                        "timestamp": time.time(),
                                        "session_id": session_id,
                                    }
                                )

                            # Execute LINE hooks with async callback
                            full_context = "\n".join(transcript_buffer)

                            def handle_line_hook_result(code):
                                if code == 100:
                                    signal_manager.set_listening(False)
                                elif code == 101:
                                    signal_manager.set_running(False)
                                    signal_manager.set_listening(False)
                                elif code == 102:
                                    signal_manager.set_running(False)
                                    signal_manager.set_listening(False)

                            hook_manager.run_hooks(
                                "line",
                                payload=full_context,
                                args=[final_text],
                                async_mode=True,
                                callback=handle_line_hook_result,
                            )

                        # Reset recognizer for next utterance
                        rec.Reset()
                        transcript_buffer = []  # Clear buffer for next utterance
                        continue

                    # Debug: Log queue processing
                    if callback_counter[0] % 100 == 1:  # Log occasionally
                        print(
                            f"DEBUG: Processing queue - data length: {len(data)} bytes, type: {type(data)}",
                            file=sys.stderr,
                        )
                        sys.stderr.flush()

                    accepted = rec.AcceptWaveform(data)

                    # Debug: Check if Vosk is accepting the data
                    if callback_counter[0] % 100 == 1:
                        print(
                            f"DEBUG: Vosk AcceptWaveform returned: {accepted}",
                            file=sys.stderr,
                        )
                        sys.stderr.flush()

                    if accepted:
                        result = json.loads(rec.Result())
                        text = result.get("text", "")
                        if text:
                            print(text)  # Stream to stdout
                            sys.stdout.flush()
                            transcript_buffer.append(text)

                            # Broadcast final transcription to IPC clients
                            if ipc_server:
                                ipc_server.broadcast_event(
                                    {
                                        "type": "transcription",
                                        "result_type": "final",
                                        "text": text,
                                        "confidence": result.get("confidence", 1.0),
                                        "timestamp": time.time(),
                                        "session_id": session_id,
                                    }
                                )

                            # Execute LINE hooks with async callback
                            full_context = "\n".join(transcript_buffer)

                            def handle_line_hook_result(code):
                                if code == 100:
                                    signal_manager.set_listening(False)
                                elif code == 101:
                                    signal_manager.set_running(False)
                                    signal_manager.set_listening(False)
                                elif code == 102:
                                    signal_manager.set_running(False)
                                    signal_manager.set_listening(False)

                            hook_manager.run_hooks(
                                "line",
                                payload=full_context,
                                args=[text],
                                async_mode=True,
                                callback=handle_line_hook_result,
                            )
                    else:
                        # Broadcast partial result if enabled
                        if ipc_server and config.ipc.send_partials:
                            partial_result = json.loads(rec.PartialResult())
                            partial_text = partial_result.get("partial", "")
                            if partial_text:
                                ipc_server.broadcast_event(
                                    {
                                        "type": "transcription",
                                        "result_type": "partial",
                                        "text": partial_text,
                                        "timestamp": time.time(),
                                        "session_id": session_id,
                                    }
                                )
                except queue.Empty:
                    pass
                except Exception as e:
                    print(f"Error processing audio: {e}", file=sys.stderr)
                    sys.stderr.flush()
            else:
                # Sleep briefly to avoid busy loop when not listening
                # Also process asyncio tasks if WebRTC is running
                if webrtc_server:
                    try:
                        loop = asyncio.get_event_loop()
                        loop.run_until_complete(asyncio.sleep(0.1))
                    except Exception:
                        time.sleep(0.1)
                else:
                    time.sleep(0.1)
                # Drain queue to avoid stale audio when we start again
                while not audio_queue.empty():
                    audio_queue.get()

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
    finally:
        if stream is not None:
            stream.stop()
            stream.close()

        # Stop recording and clean up
        if args.record_audio:
            audio_recorder.stop_recording()

        # Finalize audio processing
        audio_processor.cleanup()

        # Ensure stop hooks are run if we exit while listening or have data
        if (
            signal_manager.is_listening() or transcript_buffer
        ) and not signal_manager.is_running():
            full_transcript = "\n".join(transcript_buffer)
            print("Running final stop hooks...", file=sys.stderr)
            hook_manager.run_hooks("stop", payload=full_transcript, async_mode=True)
            # Wait for final hooks to complete (with timeout)
            hook_manager.wait_for_hooks(timeout=10.0)

        # Clean up PID file
        remove_pid(instance_name)

        # Stop WebRTC server
        if webrtc_server:
            webrtc_server.stop()

        # Stop IPC server
        if ipc_server:
            ipc_server.stop()

    print("Exiting...", file=sys.stderr)


def cmd_start(args):
    """Start listening on a named instance."""
    if send_signal_to_instance(args.name, signal.SIGUSR1):
        print(f"Sent start signal to instance '{args.name}'")
    else:
        sys.exit(1)


def cmd_stop(args):
    """Stop listening on a named instance."""
    if send_signal_to_instance(args.name, signal.SIGUSR2):
        print(f"Sent stop signal to instance '{args.name}'")
    else:
        sys.exit(1)


def cmd_terminate(args):
    """Terminate a named instance."""
    if send_signal_to_instance(args.name, signal.SIGTERM):
        print(f"Sent terminate signal to instance '{args.name}'")
    else:
        sys.exit(1)


def cmd_toggle(args):
    """Toggle listening state on a named instance."""
    from .ipc_client import ConnectionError as IPCConnectionError
    from .ipc_client import IPCClient, get_socket_path

    socket_path = get_socket_path(args.name)

    try:
        with IPCClient(socket_path) as client:
            result = client.send_command("toggle")
            action = result.get("action", "")
            if action == "started":
                print(f"✓ Listening started on instance '{args.name}'")
            elif action == "stopped":
                print(f"✓ Listening stopped on instance '{args.name}'")
            else:
                print(f"✓ Toggled listening on instance '{args.name}'")
    except IPCConnectionError:
        print(
            f"Error: Cannot connect to instance '{args.name}' (socket: {socket_path})",
            file=sys.stderr,
        )
        print("Make sure the instance is running.", file=sys.stderr)
        sys.exit(1)


def cmd_list(args):
    """List all running instances."""
    from .pid_manager import list_instances

    instances = list_instances()
    if not instances:
        print("No running instances found")
        return

    print(f"{'Name':<20} {'PID':<10}")
    print("-" * 30)
    for name, pid in instances:
        print(f"{name:<20} {pid:<10}")


def cmd_send(args):
    """Send IPC command to a running instance."""
    from .ipc_client import CommandError
    from .ipc_client import ConnectionError as IPCConnectionError
    from .ipc_client import IPCClient, get_socket_path

    socket_path = get_socket_path(args.name)

    try:
        with IPCClient(socket_path) as client:
            # Execute command
            if args.ipc_command == "toggle":
                result = client.send_command("toggle")
                action = result.get("action", "")
                if action == "started":
                    print(f"✓ Listening started on instance '{args.name}'")
                else:
                    print(f"✓ Listening stopped on instance '{args.name}'")

            elif args.ipc_command == "start":
                result = client.send_command("start")
                print(f"✓ Started listening on instance '{args.name}'")

            elif args.ipc_command == "stop":
                result = client.send_command("stop")
                print(f"✓ Stopped listening on instance '{args.name}'")

            elif args.ipc_command == "status":
                result = client.send_command("status")
                print(f"Instance: {args.name}")
                print(f"PID: {result['pid']}")
                print(f"Listening: {'Yes' if result['listening'] else 'No'}")
                print(f"Uptime: {result['uptime']:.1f}s")
                print(f"Device: {result['device']}")
                print(f"Model: {result['model']}")

            elif args.ipc_command == "transcript":
                result = client.send_command("get_transcript")
                transcript = result.get("transcript", [])
                if transcript:
                    for line in transcript:
                        print(line)
                else:
                    print("(no transcript yet)")

            elif args.ipc_command == "devices":
                result = client.send_command("get_devices")
                devices = result.get("devices", [])
                current = result.get("current_device")
                print(f"{'ID':<5} {'Name':<40} {'Channels':<10} {'Current':<10}")
                print("-" * 70)
                for dev in devices:
                    is_current = "✓" if dev["id"] == current else ""
                    print(
                        f"{dev['id']:<5} {dev['name']:<40} {dev['channels']:<10} {is_current:<10}"
                    )

            elif args.ipc_command == "webrtc_status":
                result = client.send_command("get_webrtc_status")
                if (
                    "error" in result
                    and result["error"]["code"] == "WEBRTC_NOT_AVAILABLE"
                ):
                    print(f"WebRTC not available: {result['error']['message']}")
                else:
                    print(
                        f"WebRTC Server: {'Running' if result.get('running', False) else 'Not running'}"
                    )
                    if result.get("running"):
                        print(
                            f"Host: {result.get('host', 'unknown')}:{result.get('port', 'unknown')}"
                        )
                        print(
                            f"Active connections: {result.get('active_connections', 0)}"
                        )
                        print(f"Max connections: {result.get('max_connections', 0)}")

            elif args.ipc_command == "start_webrtc":
                result = client.send_command("start_webrtc")
                if (
                    "error" in result
                    and result["error"]["code"] == "WEBRTC_NOT_AVAILABLE"
                ):
                    print(f"WebRTC not available: {result['error']['message']}")
                elif result.get("webrtc_running"):
                    print(f"✓ WebRTC server is running on instance '{args.name}'")
                else:
                    print(f"✗ WebRTC server failed to start on instance '{args.name}'")

            elif args.ipc_command == "stop_webrtc":
                result = client.send_command("stop_webrtc")
                if (
                    "error" in result
                    and result["error"]["code"] == "WEBRTC_NOT_AVAILABLE"
                ):
                    print(f"WebRTC not available: {result['error']['message']}")
                elif result.get("webrtc_stopped"):
                    print(f"✓ WebRTC server stopped on instance '{args.name}'")
                else:
                    print(f"✗ WebRTC server failed to stop on instance '{args.name}'")

    except IPCConnectionError:
        print(f"Error: Cannot connect to instance '{args.name}'", file=sys.stderr)
        print(f"Socket: {socket_path}", file=sys.stderr)
        print("Is the daemon running? Try: vosk-wrapper-1000 list", file=sys.stderr)
        sys.exit(1)
    except CommandError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_stream(args):
    """Stream live transcription (automatically starts/stops daemon if needed)."""
    import subprocess
    import time
    from .ipc_client import ConnectionError as IPCConnectionError
    from .ipc_client import IPCClient, get_socket_path
    from .pid_manager import list_instances

    socket_path = get_socket_path(args.name)
    daemon_started_by_us = False
    daemon_proc = None

    # Check if instance is already running
    running_instances = list_instances()
    instance_running = any(name == args.name for name, _ in running_instances)

    if not instance_running:
        if args.no_auto_start:
            print(f"Error: Instance '{args.name}' is not running", file=sys.stderr)
            print("Start the daemon manually with:", file=sys.stderr)
            print(f"  vosk-wrapper-1000 daemon --name {args.name}", file=sys.stderr)
            sys.exit(1)

        # Auto-start the daemon
        print(f"Starting daemon instance '{args.name}'...", file=sys.stderr)
        daemon_cmd = [
            sys.executable,
            "-m",
            "vosk_wrapper_1000.main",
            "daemon",
            "--name",
            args.name,
            "--model",
            args.model,
        ]

        if args.device:
            daemon_cmd.extend(["--device", args.device])

        try:
            daemon_proc = subprocess.Popen(
                daemon_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            daemon_started_by_us = True

            # Wait for daemon to be ready
            print("Waiting for daemon to initialize...", file=sys.stderr)
            max_retries = 15
            for attempt in range(max_retries):
                time.sleep(1)
                try:
                    with IPCClient(socket_path, timeout=1.0) as test_client:
                        test_client.send_command("status")
                        break
                except:
                    if attempt == max_retries - 1:
                        print(
                            "Failed to connect to daemon after startup", file=sys.stderr
                        )
                        if daemon_proc:
                            daemon_proc.terminate()
                        sys.exit(1)
                    continue

            print(f"Daemon started successfully", file=sys.stderr)

        except Exception as e:
            print(f"Failed to start daemon: {e}", file=sys.stderr)
            sys.exit(1)

    try:
        with IPCClient(socket_path) as client:
            # Subscribe to events
            events = ["transcription", "status", "ready"]
            client.subscribe(events)

            print(f"Streaming from instance '{args.name}' (Ctrl+C to stop)...")
            print()

            # Check if already listening, start if not
            try:
                status = client.send_command("status")
                if not status.get("listening", False):
                    print("Starting listening...", file=sys.stderr)
                    client.send_command("start")
            except:
                pass  # Ignore status check errors

            start_time = time.time()
            last_activity = start_time

            # Stream events
            for event in client.stream_events():
                current_time = time.time()

                # Check for timeout when auto-started
                if daemon_started_by_us and current_time - start_time > args.timeout:
                    print(
                        f"\nTimeout reached ({args.timeout}s), stopping...",
                        file=sys.stderr,
                    )
                    break

                event_type = event.get("type")

                if event_type == "ready":
                    print(
                        f"[READY] Service ready - PID: {event.get('pid')}, Device: {event.get('device')}"
                    )

                elif event_type == "transcription":
                    result_type = event.get("result_type")
                    text = event.get("text", "")

                    if result_type == "partial":
                        if not args.no_partials:
                            print(f"\r[PARTIAL] {text}", end="", flush=True)
                    elif result_type == "final":
                        if not args.no_partials:
                            print("\r" + " " * 80 + "\r", end="")  # Clear partial line
                        print(f"[FINAL] {text}")
                        last_activity = current_time

                        # If auto-started and we got a final result, we can stop after a brief pause
                        if daemon_started_by_us and current_time - last_activity > 2.0:
                            print("Speech completed, stopping...", file=sys.stderr)
                            break

                elif event_type == "status_change":
                    event_name = event.get("event", "")
                    if event_name == "listening_started":
                        print("[STATUS] Listening started")
                    elif event_name == "listening_stopped":
                        print("[STATUS] Listening stopped")
                        if daemon_started_by_us:
                            break

            # Stop listening
            try:
                client.send_command("stop")
            except:
                pass  # Ignore stop errors

    except IPCConnectionError:
        print(f"Error: Cannot connect to instance '{args.name}'", file=sys.stderr)
        print(f"Socket: {socket_path}", file=sys.stderr)
        if not daemon_started_by_us:
            print("Is the daemon running? Try: vosk-wrapper-1000 list", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nStream interrupted by user", file=sys.stderr)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

    finally:
        # Clean up daemon if we started it
        if daemon_started_by_us:
            try:
                from .pid_manager import send_signal_to_instance

                send_signal_to_instance(args.name, signal.SIGTERM)
                print(f"Terminated auto-started daemon '{args.name}'", file=sys.stderr)
            except:
                pass  # Ignore cleanup errors

            if daemon_proc:
                try:
                    daemon_proc.wait(timeout=5.0)
                except:
                    daemon_proc.kill()


def cmd_transcribe_file(args):
    """Transcribe a WAV file using the audio processing pipeline."""
    import wave
    import numpy as np

    # Initialize config manager
    config_manager = ConfigManager()

    # Initialize model manager
    model_manager = ModelManager()

    # Resolve model path (support short names like "vosk-model-en-gb-0.1")
    try:
        resolved_model_path = model_manager.resolve_model_path(args.model)
        args.model = str(resolved_model_path)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Set Vosk log level to match application log level
    log_level = getattr(args, "_final_log_level", "WARNING")
    set_vosk_log_level(log_level)

    # Get model sample rate
    model_sample_rate = model_manager.get_model_sample_rate(args.model)

    print(f"Loading model from {args.model}...", file=sys.stderr)
    import vosk

    model = vosk.Model(str(args.model))

    # Open WAV file
    try:
        with wave.open(args.file, "rb") as wf:
            # Get WAV file properties
            channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            nframes = wf.getnframes()

            print(f"Input file: {args.file}", file=sys.stderr)
            print(f"  Channels: {channels}", file=sys.stderr)
            print(f"  Sample width: {sampwidth} bytes", file=sys.stderr)
            print(f"  Sample rate: {framerate} Hz", file=sys.stderr)
            print(f"  Duration: {nframes / framerate:.2f} seconds", file=sys.stderr)

            if sampwidth != 2:
                print(
                    f"Error: Only 16-bit (2 byte) WAV files are supported",
                    file=sys.stderr,
                )
                sys.exit(1)

            if channels > 1:
                print(
                    f"  Note: Converting {channels}-channel audio to mono",
                    file=sys.stderr,
                )

            # Initialize audio processor
            audio_processor = AudioProcessor(
                device_rate=framerate,
                model_rate=model_sample_rate,
                noise_filter_enabled=not args.disable_noise_reduction,
                noise_reduction_strength=args.noise_reduction_level,
                stationary_noise=args.stationary_noise
                and not args.non_stationary_noise,
                silence_threshold=args.silence_threshold,
                normalize_audio=args.normalize_audio,
                normalization_target_level=args.normalize_target_level,
                vad_hysteresis_chunks=getattr(args, "vad_hysteresis", 10),
                noise_reduction_min_rms_ratio=getattr(
                    args, "noise_reduction_min_rms_ratio", 0.5
                ),
                pre_roll_duration=getattr(args, "pre_roll_duration", 1.0),
            )

            # Create recognizer
            if args.grammar:
                print(f"Using grammar: {args.grammar}", file=sys.stderr)
                rec = vosk.KaldiRecognizer(model, model_sample_rate, args.grammar)
            else:
                rec = vosk.KaldiRecognizer(model, model_sample_rate)

            # Configure recognizer options
            if args.words:
                rec.SetWords(True)

            if args.partial_words:
                rec.SetPartialWords(True)

            if getattr(args, "max_alternatives", 1) > 1:
                rec.SetMaxAlternatives(args.max_alternatives)

            if getattr(args, "max_alternatives", 1) > 1:
                rec.SetMaxAlternatives(args.max_alternatives)

            # Setup audio recorder if requested
            audio_recorder = None
            if args.record_audio:
                audio_recorder = AudioRecorder(args.record_audio, model_sample_rate)
                if not audio_recorder.start_recording():
                    print(
                        f"Error opening recording file {args.record_audio}",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                print(
                    f"Recording processed audio to: {args.record_audio}",
                    file=sys.stderr,
                )

            print(
                f"Processing audio (model expects {model_sample_rate} Hz)...",
                file=sys.stderr,
            )

            # Process audio in chunks
            chunk_size = 4000  # Process 4000 frames at a time
            transcript_lines = []

            while True:
                data = wf.readframes(chunk_size)
                if len(data) == 0:
                    break

                # Convert bytes to numpy array
                audio_chunk = np.frombuffer(data, dtype=np.int16)

                # Convert to mono first (silence detection must be done before other processing)
                if channels > 1:
                    # Reshape interleaved multi-channel data to (frames, channels)
                    frames = len(audio_chunk) // channels
                    audio_multi = audio_chunk.reshape(frames, channels)
                    # Average all channels to create mono
                    mono_chunk = np.mean(audio_multi, axis=1).astype(np.int16)
                else:
                    mono_chunk = audio_chunk

                # Check if audio contains meaningful sound (silence detection first)
                if not audio_processor.has_audio(mono_chunk):
                    continue

                # Process audio through pipeline (mono conversion already done)
                processed_audio = audio_processor._process_mono_audio_chunk(mono_chunk)

                # Save to recording file if enabled
                if audio_recorder:
                    audio_recorder.write_audio(processed_audio)

                # Send to Vosk
                if rec.AcceptWaveform(bytes(processed_audio)):
                    result = json.loads(rec.Result())
                    # Handle alternatives if enabled
                    if "alternatives" in result and result["alternatives"]:
                        # Use the first (best) alternative
                        text = result["alternatives"][0].get("text", "")
                    else:
                        text = result.get("text", "")
                    if text:
                        transcript_lines.append(text)

            # Get final result
            final_result = json.loads(rec.FinalResult())
            # Handle alternatives if enabled
            if "alternatives" in final_result and final_result["alternatives"]:
                # Use the first (best) alternative
                final_text = final_result["alternatives"][0].get("text", "")
            else:
                final_text = final_result.get("text", "")
            if final_text:
                transcript_lines.append(final_text)

            # Cleanup
            audio_processor.cleanup()
            if audio_recorder:
                audio_recorder.stop_recording()

            # Print results
            print(
                f"\nTranscription complete. Total lines: {len(transcript_lines)}",
                file=sys.stderr,
            )
            print(f"--- Transcript ---", file=sys.stderr)
            for line in transcript_lines:
                print(line)

    except FileNotFoundError:
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)
    except wave.Error as e:
        print(f"Error reading WAV file: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


def main():
    # Get XDG default paths
    default_model = ModelManager().default_model
    default_hooks_dir = get_hooks_dir()

    parser = argparse.ArgumentParser(
        description="Vosk Speech Recognition Service - Control multiple voice recognition instances",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
 Examples:
  # Run a daemon instance (noise filtering enabled by default)
  vosk-wrapper-1000 daemon --name my-instance

  # Configure noise filtering
  vosk-wrapper-1000 daemon --noise-reduction 0.3 --non-stationary-noise

  # Record processed audio for review
  vosk-wrapper-1000 daemon --record-audio output.wav

  # Control instances
  vosk-wrapper-1000 list
  vosk-wrapper-1000 start my-instance
  vosk-wrapper-1000 stop my-instance
  vosk-wrapper-1000 terminate my-instance

For more information, visit: https://github.com/rwese/vosk-wrapper-1000-py
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Daemon command (runs as background service)
    daemon_parser = subparsers.add_parser(
        "daemon", help="Run voice recognition service as daemon"
    )
    daemon_parser.add_argument(
        "--name",
        type=str,
        default="default",
        help="Instance name for managing multiple processes (default: default)",
    )
    daemon_parser.add_argument(
        "--model",
        type=str,
        default=default_model,
        help=f"Path to Vosk model directory (default: {default_model})",
    )
    daemon_parser.add_argument(
        "--device", type=str, default=None, help="Input device ID or Name substring"
    )
    daemon_parser.add_argument(
        "--samplerate",
        type=int,
        default=16000,
        help="Sample rate in Hz (default: auto-detect from model)",
    )
    daemon_parser.add_argument(
        "--hooks-dir",
        type=str,
        default=default_hooks_dir,
        help=f"Path to hooks directory (default: {default_hooks_dir})",
    )
    daemon_parser.add_argument(
        "--list-devices", action="store_true", help="List available audio input devices"
    )
    daemon_parser.add_argument(
        "--foreground",
        action="store_true",
        help="Run in foreground (default: run as daemon in background)",
    )

    # Vosk recognition options
    daemon_parser.add_argument(
        "--words",
        action="store_true",
        help="Enable word-level timestamps in recognition output",
    )
    daemon_parser.add_argument(
        "--partial-words",
        action="store_true",
        help="Enable partial word results during recognition",
    )
    daemon_parser.add_argument(
        "--grammar",
        type=str,
        default=None,
        help="Grammar/vocabulary to restrict recognition (space-separated words)",
    )
    daemon_parser.add_argument(
        "--max-alternatives",
        type=int,
        default=1,
        help="Maximum number of alternative transcriptions to return (default: 1)",
    )

    # Audio processing options
    daemon_parser.add_argument(
        "--disable-noise-reduction",
        action="store_true",
        help="Disable noise reduction (enabled by default)",
    )
    daemon_parser.add_argument(
        "--noise-reduction-level",
        type=float,
        default=0.05,
        help="Noise reduction strength (0.0-1.0, default: 0.05)",
    )
    daemon_parser.add_argument(
        "--stationary-noise",
        action="store_true",
        help="Use stationary noise reduction (faster)",
    )
    daemon_parser.add_argument(
        "--non-stationary-noise",
        action="store_true",
        default=True,
        help="Use non-stationary noise reduction (slower but more adaptive, default: True)",
    )
    daemon_parser.add_argument(
        "--noise-reduction-min-rms-ratio",
        type=float,
        default=0.5,
        help="Minimum RMS ratio after noise reduction (0.0-1.0, default: 0.5). If noise reduction reduces RMS below this ratio, it will be skipped.",
    )
    daemon_parser.add_argument(
        "--silence-threshold",
        type=float,
        default=50.0,
        help="RMS threshold for audio detection - audio below this is skipped (default: 50.0)",
    )
    daemon_parser.add_argument(
        "--vad-hysteresis",
        type=int,
        default=10,
        help="Number of consecutive silent chunks before exiting speech mode (default: 10)",
    )
    daemon_parser.add_argument(
        "--pre-roll-duration",
        type=float,
        default=2.0,
        help="Duration in seconds of audio to buffer before speech detection (default: 2.0)",
    )
    daemon_parser.add_argument(
        "--normalize-audio",
        action="store_true",
        help="Enable audio normalization to ensure consistent levels",
    )
    daemon_parser.add_argument(
        "--normalize-target-level",
        type=float,
        default=0.3,
        help="Target RMS level for normalization (0.0-1.0, default: 0.3)",
    )
    daemon_parser.add_argument(
        "--record-audio",
        type=str,
        help="Record processed audio sent to Vosk to WAV file for review",
    )
    daemon_parser.add_argument(
        "--log-level",
        type=str,
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level (default: WARNING, can also be set via VOSK_LOG_LEVEL env var)",
    )

    # WebRTC options
    daemon_parser.add_argument(
        "--webrtc-enabled",
        action="store_true",
        help="Enable WebRTC server for browser-based connections",
    )
    daemon_parser.add_argument(
        "--webrtc-port",
        type=int,
        default=8080,
        help="WebRTC server port (default: 8080)",
    )
    daemon_parser.add_argument(
        "--webrtc-host",
        type=str,
        default="0.0.0.0",
        help="WebRTC server host (default: 0.0.0.0)",
    )

    # Control commands
    start_parser = subparsers.add_parser(
        "start", help="Start listening on a running instance"
    )
    start_parser.add_argument(
        "name", nargs="?", default="default", help="Instance name"
    )

    stop_parser = subparsers.add_parser(
        "stop", help="Stop listening on a running instance"
    )
    stop_parser.add_argument("name", nargs="?", default="default", help="Instance name")

    terminate_parser = subparsers.add_parser(
        "terminate", help="Terminate a running instance"
    )
    terminate_parser.add_argument(
        "name", nargs="?", default="default", help="Instance name"
    )

    toggle_parser = subparsers.add_parser(
        "toggle", help="Toggle listening state on a running instance"
    )
    toggle_parser.add_argument(
        "name", nargs="?", default="default", help="Instance name"
    )

    subparsers.add_parser("list", help="List all running instances")

    # IPC send command
    send_parser = subparsers.add_parser(
        "send", help="Send IPC command to a running instance"
    )
    send_parser.add_argument(
        "ipc_command",
        choices=[
            "start",
            "stop",
            "toggle",
            "status",
            "transcript",
            "devices",
            "webrtc_status",
            "start_webrtc",
            "stop_webrtc",
        ],
        help="Command to send",
    )
    send_parser.add_argument(
        "--name", "-n", default="default", help="Instance name (default: default)"
    )

    # IPC stream command
    stream_parser = subparsers.add_parser(
        "stream", help="Stream live transcription (automatically starts/stops daemon)"
    )
    stream_parser.add_argument(
        "--name", "-n", default="default", help="Instance name (default: default)"
    )
    stream_parser.add_argument(
        "--no-partials",
        action="store_true",
        help="Don't show partial results, only final transcriptions",
    )
    stream_parser.add_argument(
        "--auto-start",
        action="store_true",
        default=True,
        help="Automatically start daemon if not running (default: enabled)",
    )
    stream_parser.add_argument(
        "--no-auto-start",
        action="store_true",
        help="Don't automatically start daemon, require it to be running already",
    )
    stream_parser.add_argument(
        "--model",
        type=str,
        default=default_model,
        help=f"Path to Vosk model directory (used when auto-starting daemon, default: {default_model})",
    )
    stream_parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Input device ID or Name substring (used when auto-starting daemon)",
    )
    stream_parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Maximum time to wait for speech in seconds when auto-starting (default: 120.0)",
    )

    # Transcribe file command
    transcribe_parser = subparsers.add_parser(
        "transcribe-file",
        help="Transcribe a WAV file using the audio processing pipeline",
    )
    transcribe_parser.add_argument(
        "file", help="Path to WAV file to transcribe (must be mono, 16-bit)"
    )
    transcribe_parser.add_argument(
        "--model",
        type=str,
        default=default_model,
        help=f"Path to Vosk model directory (default: {default_model})",
    )

    # Audio processing options (same as daemon)
    transcribe_parser.add_argument(
        "--disable-noise-reduction",
        action="store_true",
        help="Disable noise reduction (enabled by default)",
    )
    transcribe_parser.add_argument(
        "--noise-reduction-level",
        type=float,
        default=0.05,
        help="Noise reduction strength (0.0-1.0, default: 0.05)",
    )
    transcribe_parser.add_argument(
        "--stationary-noise",
        action="store_true",
        help="Use stationary noise reduction (faster)",
    )
    transcribe_parser.add_argument(
        "--non-stationary-noise",
        action="store_true",
        default=True,
        help="Use non-stationary noise reduction (slower but more adaptive, default: True)",
    )
    transcribe_parser.add_argument(
        "--noise-reduction-min-rms-ratio",
        type=float,
        default=0.5,
        help="Minimum RMS ratio after noise reduction (0.0-1.0, default: 0.5). If noise reduction reduces RMS below this ratio, it will be skipped.",
    )
    transcribe_parser.add_argument(
        "--silence-threshold",
        type=float,
        default=50.0,
        help="RMS threshold for audio detection - audio below this is skipped (default: 50.0)",
    )
    transcribe_parser.add_argument(
        "--vad-hysteresis",
        type=int,
        default=10,
        help="Number of consecutive silent chunks before exiting speech mode (default: 10)",
    )
    transcribe_parser.add_argument(
        "--pre-roll-duration",
        type=float,
        default=2.0,
        help="Duration in seconds of audio to buffer before speech detection (default: 2.0)",
    )
    transcribe_parser.add_argument(
        "--normalize-audio",
        action="store_true",
        help="Enable audio normalization to ensure consistent levels",
    )
    transcribe_parser.add_argument(
        "--normalize-target-level",
        type=float,
        default=0.3,
        help="Target RMS level for normalization (0.0-1.0, default: 0.3)",
    )
    transcribe_parser.add_argument(
        "--record-audio",
        type=str,
        help="Record processed audio sent to Vosk to WAV file for comparison",
    )

    # Vosk recognition options
    transcribe_parser.add_argument(
        "--words",
        action="store_true",
        help="Enable word-level timestamps in recognition output",
    )
    transcribe_parser.add_argument(
        "--partial-words",
        action="store_true",
        help="Enable partial word results during recognition",
    )
    transcribe_parser.add_argument(
        "--grammar",
        type=str,
        default=None,
        help="Grammar/vocabulary to restrict recognition (space-separated words)",
    )
    transcribe_parser.add_argument(
        "--max-alternatives",
        type=int,
        default=1,
        help="Maximum number of alternative transcriptions to return (default: 1)",
    )

    args = parser.parse_args()

    # Setup logging based on args, environment, or config file
    log_level = getattr(args, "log_level", None)
    config_manager = ConfigManager()
    final_log_level = setup_logging(log_level, config_manager)

    # Store the final log level in args for commands to access
    args._final_log_level = final_log_level

    if args.command == "daemon":
        run_service(args)
    elif args.command == "start":
        cmd_start(args)
    elif args.command == "stop":
        cmd_stop(args)
    elif args.command == "terminate":
        cmd_terminate(args)
    elif args.command == "toggle":
        cmd_toggle(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "send":
        cmd_send(args)
    elif args.command == "stream":
        cmd_stream(args)
    elif args.command == "transcribe-file":
        cmd_transcribe_file(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
