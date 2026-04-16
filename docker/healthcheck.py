#!/usr/bin/env python3
"""
AI News Aggregator - Health Check Server
Lightweight HTTP server for Docker healthcheck and monitoring.
Responds on /health with status information.
"""

import json
import socket
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import os


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler for health checks"""

    def do_GET(self):
        if self.path == "/health":
            self._respond_healthy()
        elif self.path == "/ready":
            self._respond_ready()
        else:
            self.send_response(404)
            self.end_headers()

    def _respond_healthy(self):
        """Basic liveness check — if this responds, the process is alive"""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "healthy"}).encode())

    def _respond_ready(self):
        """Readiness check — verifies dependencies are reachable"""
        checks = {}

        # Check PostgreSQL
        db_host = os.getenv("DB_HOST", "postgres")
        db_port = int(os.getenv("DB_PORT", "5432"))
        checks["postgres"] = _tcp_check(db_host, db_port)

        # Check Redis
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        checks["redis"] = _tcp_check(redis_host, redis_port)

        # Check Ollama (optional, don't fail on it)
        ollama_url = os.getenv("OLLAMA_BASE_URL", "")
        if ollama_url:
            ollama_host = ollama_url.replace("http://", "").replace("https://", "").split(":")[0]
            ollama_port = int(ollama_url.split(":")[-1].rstrip("/")) if ":" in ollama_url[7:] else 11434
            checks["ollama"] = _tcp_check(ollama_host, ollama_port)

        # Overall: ready if core deps are up
        core_healthy = checks.get("postgres", False) and checks.get("redis", False)
        status_code = 200 if core_healthy else 503
        status_text = "ready" if core_healthy else "degraded"

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": status_text,
            "checks": checks,
        }).encode())

    def log_message(self, format, *args):
        """Suppress default logging"""
        pass


def _tcp_check(host: str, port: int, timeout: float = 3.0) -> bool:
    """Check if a TCP port is reachable"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            return result == 0
    except (socket.gaierror, OSError):
        return False


def run_server(port: int = 8080):
    """Start the health check HTTP server"""
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AI News Aggregator Health Check")
    parser.add_argument("--check", action="store_true", help="Run a one-shot health check against the running server")
    parser.add_argument("--port", type=int, default=None, help="Port to check")
    args = parser.parse_args()
    
    if args.check:
        # One-shot check mode: query the running healthcheck server
        port = args.port or int(os.getenv("HEALTHCHECK_PORT", "8080"))
        try:
            import urllib.request
            # Check /ready endpoint (verifies dependencies)
            url = f"http://localhost:{port}/ready"
            req = urllib.request.Request(url, timeout=5)
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read().decode())
            if data.get("status") == "ready":
                print("healthy")
                sys.exit(0)
            else:
                print(f"degraded: {data}")
                sys.exit(1)
        except Exception as e:
            # Fall back to basic liveness check
            try:
                url = f"http://localhost:{port}/health"
                resp = urllib.request.urlopen(url, timeout=5)
                print("alive (dependencies not ready)")
                sys.exit(0)
            except Exception:
                print(f"unhealthy: {e}")
                sys.exit(1)
    else:
        # Server mode (run by entrypoint)
        port = int(os.getenv("HEALTHCHECK_PORT", "8080"))
        print(f"[healthcheck] Starting health check server on port {port}")
        try:
            run_server(port)
        except KeyboardInterrupt:
            pass