#!/usr/bin/env python3
"""
Standalone HTTP Server for WebRTC Client

This script serves the WebRTC client HTML file on a local HTTP server.
It's a simple alternative to the full webrtc_demo.py script when you
already have the daemon running separately.

Usage:
    python serve_client.py [--port PORT] [--https]

Examples:
    # Serve on default port 8001
    python serve_client.py

    # Serve on custom port
    python serve_client.py --port 9000

    # Serve with HTTPS (requires cert.pem and key.pem)
    python serve_client.py --https
"""

import argparse
import http.server
import os
import socketserver
import ssl
import sys
from pathlib import Path


class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler with CORS support."""

    def end_headers(self):
        """Add CORS headers to all responses."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS preflight."""
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        """Log messages with better formatting."""
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Serve WebRTC client HTML on local HTTP server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Serve on http://localhost:8001
  %(prog)s --port 9000        # Serve on http://localhost:9000
  %(prog)s --https            # Serve on https://localhost:8001
  %(prog)s --host 0.0.0.0     # Allow external connections

The WebRTC client will be available at:
  http://localhost:PORT/webrtc_client.html

Make sure the vosk-wrapper-1000 daemon is running with WebRTC enabled:
  python -m vosk_wrapper_1000.main daemon --webrtc-enabled --webrtc-port 8080
        """,
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Port to serve on (default: 8001)",
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind to (default: localhost, use 0.0.0.0 for all interfaces)",
    )
    parser.add_argument(
        "--https",
        action="store_true",
        help="Use HTTPS (requires cert.pem and key.pem in current directory)",
    )
    parser.add_argument(
        "--webrtc-port",
        type=int,
        default=8080,
        help="WebRTC server port (for display only, default: 8080)",
    )

    args = parser.parse_args()

    # Change to the webrtc directory where the HTML file is located
    webrtc_dir = Path(__file__).parent
    os.chdir(webrtc_dir)

    # Verify HTML file exists
    if not Path("webrtc_client.html").exists():
        print("❌ Error: webrtc_client.html not found in current directory")
        print(f"   Current directory: {webrtc_dir}")
        sys.exit(1)

    # Setup HTTPS if requested
    protocol = "http"
    context = None

    if args.https:
        cert_file = Path("cert.pem")
        key_file = Path("key.pem")

        # Generate self-signed certificate if not present
        if not cert_file.exists() or not key_file.exists():
            print("📜 Generating self-signed certificate...")
            import subprocess

            result = subprocess.run(
                [
                    "openssl",
                    "req",
                    "-x509",
                    "-newkey",
                    "rsa:4096",
                    "-keyout",
                    "key.pem",
                    "-out",
                    "cert.pem",
                    "-days",
                    "365",
                    "-nodes",
                    "-subj",
                    "/C=US/ST=State/L=City/O=Organization/CN=localhost",
                ],
                capture_output=True,
            )

            if result.returncode != 0:
                print("❌ Failed to generate certificate")
                print("   Make sure openssl is installed")
                sys.exit(1)

            print("✅ Certificate generated successfully")

        # Setup SSL context
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")
        protocol = "https"

    # Create HTTP server
    try:
        with socketserver.TCPServer(
            (args.host, args.port), CORSHTTPRequestHandler
        ) as httpd:
            # Wrap socket with SSL if HTTPS is requested
            if context:
                httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

            print("=" * 60)
            print("🌐 WebRTC Client Server")
            print("=" * 60)
            print(f"Serving at: {protocol}://{args.host}:{args.port}")
            print(f"\n📄 Open in browser:")
            print(f"   {protocol}://{args.host}:{args.port}/webrtc_client.html")
            print(f"\n🎤 WebRTC server should be running at:")
            print(f"   http://localhost:{args.webrtc_port}")
            print(f"\n💡 Tips:")
            print(f"   - Make sure vosk-wrapper-1000 daemon is running with --webrtc-enabled")
            print(f"   - Grant microphone permissions when prompted by browser")
            print(f"   - For HTTPS, browser may warn about self-signed certificate")
            print(f"\n🛑 Press Ctrl+C to stop the server")
            print("=" * 60)
            print()

            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\n\n🛑 Shutting down server...")
                return 0

    except OSError as e:
        if e.errno == 98:  # Address already in use
            print(f"❌ Error: Port {args.port} is already in use")
            print(f"   Try a different port: python {sys.argv[0]} --port <PORT>")
        else:
            print(f"❌ Error starting server: {e}")
        return 1

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
