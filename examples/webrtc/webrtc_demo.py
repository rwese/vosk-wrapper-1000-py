#!/usr/bin/env python3
"""
WebRTC Demo Script for vosk-wrapper-1000

This script starts both:
1. The vosk-wrapper-1000 daemon with WebRTC enabled
2. An HTTP server to serve the WebRTC client HTML

Usage:
    python webrtc_demo.py [options]

Options:
    --model PATH          Path to Vosk model (default: auto-detect)
    --webrtc-port PORT    WebRTC server port (default: 8080)
    --http-port PORT      HTTP server port for client (default: 8000)
    --https               Use HTTPS for client server (requires cert.pem/key.pem)
    --help               Show this help message
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# Add the src directory to Python path so we can import the modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import aiortc
        import av
    except ImportError as e:
        print(f"❌ Missing WebRTC dependencies: {e}")
        print("Install with: pip install aiortc av")
        return False

    try:
        import vosk
    except ImportError:
        print("❌ Missing vosk dependency")
        print("Install with: pip install vosk")
        return False

    return True


def find_model():
    """Find an available Vosk model."""
    model_dir = Path.home() / ".local" / "share" / "vosk-wrapper-1000" / "models"

    if not model_dir.exists():
        print(f"❌ No models directory found at {model_dir}")
        print("Download a model first with: vosk-download-model-1000 --list")
        return None

    # Look for common model names
    preferred_models = [
        "vosk-model-en-us-0.22",
    ]

    for model_name in preferred_models:
        model_path = model_dir / model_name
        if model_path.exists():
            return str(model_path)

    # Use any available model
    for item in model_dir.iterdir():
        if item.is_dir():
            return str(item)

    print(f"❌ No models found in {model_dir}")
    return None


def start_daemon(model_path, webrtc_port):
    """Start the vosk-wrapper-1000 daemon with WebRTC enabled."""
    cmd = [
        sys.executable,
        "-m",
        "vosk_wrapper_1000.main",
        "daemon",
        "--webrtc-enabled",
        "--webrtc-port",
        str(webrtc_port),
        "--model",
        model_path,
        "--name",
        "webrtc-demo",
    ]

    print(f"🚀 Starting daemon: {' '.join(cmd)}")

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        # Wait a bit for the daemon to start
        time.sleep(30)

        # Check if process is still running
        if process.poll() is None:
            print("✅ Daemon started successfully")
            return process
        else:
            stdout, stderr = process.communicate()
            print("❌ Daemon failed to start:")
            print("STDOUT:", stdout)
            print("STDERR:", stderr)
            return None

    except Exception as e:
        print(f"❌ Failed to start daemon: {e}")
        return None


def start_http_server(port, use_https=False):
    """Start HTTP/HTTPS server to serve the client."""
    import http.server
    import socketserver
    import ssl

    # Change to the webrtc directory
    webrtc_dir = Path(__file__).parent
    os.chdir(webrtc_dir)

    if use_https:
        # Check for certificates
        cert_file = webrtc_dir / "cert.pem"
        key_file = webrtc_dir / "key.pem"

        if not cert_file.exists() or not key_file.exists():
            print("📜 Generating self-signed certificates...")
            os.system(
                'openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"'
            )

        class HTTPServer(socketserver.TCPServer):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")
                self.socket = context.wrap_socket(self.socket, server_side=True)

        httpd = HTTPServer(("", port), http.server.SimpleHTTPRequestHandler)
        protocol = "https"
    else:
        httpd = socketserver.TCPServer(("", port), http.server.SimpleHTTPRequestHandler)
        protocol = "http"

    print(f"🌐 HTTP server started on {protocol}://localhost:{port}")
    print(f"📄 Open {protocol}://localhost:{port}/webrtc_client.html in your browser")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 HTTP server stopped")


def check_webrtc_status():
    """Check if WebRTC server is running."""
    try:
        # Try to connect to the IPC socket
        from vosk_wrapper_1000.ipc_client import IPCClient, get_socket_path

        socket_path = get_socket_path("webrtc-demo")
        with IPCClient(socket_path, timeout=2.0) as client:
            result = client.send_command("get_webrtc_status")
            if result.get("running"):
                print("✅ WebRTC server is running")
                print(f"   Host: {result.get('host')}:{result.get('port')}")
                print(f"   Active connections: {result.get('active_connections', 0)}")
                return True
            else:
                print("❌ WebRTC server is not running")
                return False
    except Exception as e:
        print(f"❌ Cannot connect to daemon: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="WebRTC Demo for vosk-wrapper-1000")
    parser.add_argument("--model", help="Path to Vosk model")
    parser.add_argument(
        "--webrtc-port", type=int, default=8080, help="WebRTC server port"
    )
    parser.add_argument("--http-port", type=int, default=8001, help="HTTP server port")
    parser.add_argument(
        "--https", action="store_true", help="Use HTTPS for client server"
    )

    args = parser.parse_args()

    print("🎤 vosk-wrapper-1000 WebRTC Demo")
    print("=" * 40)

    # Check dependencies
    if not check_dependencies():
        return 1

    # Find model
    model_path = args.model or find_model()
    if not model_path:
        return 1

    print(f"📚 Using model: {model_path}")

    # Start daemon
    daemon_process = start_daemon(model_path, args.webrtc_port)
    if not daemon_process:
        return 1

    # Wait for WebRTC to initialize
    print("⏳ Waiting for WebRTC server to initialize...")
    time.sleep(5)

    # Check WebRTC status
    if not check_webrtc_status():
        print("❌ WebRTC server failed to start properly")
        daemon_process.terminate()
        return 1

    print("\n🎉 Setup complete!")
    print("📋 Instructions:")
    print(
        f"   1. Open http{'s' if args.https else ''}://localhost:{args.http_port}/webrtc_client.html in your browser"
    )
    print("   2. Click 'Connect to Server'")
    print("   3. Grant microphone permissions when prompted")
    print("   4. Click 'Start Recognition' to begin speech recognition")
    print("\n🛑 Press Ctrl+C to stop all servers")

    try:
        # Start HTTP server in main thread
        start_http_server(args.http_port, args.https)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")

    # Clean up daemon
    if daemon_process and daemon_process.poll() is None:
        print("🛑 Terminating daemon...")
        daemon_process.terminate()
        try:
            daemon_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            daemon_process.kill()

    print("👋 Demo ended")
    return 0


if __name__ == "__main__":
    sys.exit(main())
