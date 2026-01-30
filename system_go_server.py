#!/usr/bin/env python3
"""
System GO Server - Test Execution Backend
==========================================

A lightweight server that:
1. Serves the System GO UI
2. Executes pytest tests with streaming output
3. Streams results back to the UI via Server-Sent Events

Usage:
    python3 system_go_server.py
    
Then open: http://127.0.0.1:9001
"""

import os
import sys
import json
import time
import signal
import logging
import subprocess
import threading
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Optional, Generator, Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("system_go_server")

# Configuration
SERVER_PORT = 9001
RANGERIO_BACKEND = "http://127.0.0.1:9000"
SCRIPT_DIR = Path(__file__).parent.absolute()
REPORTS_DIR = SCRIPT_DIR / "reports" / "user_scenarios"

# Ensure reports directory exists
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Model configurations
MODEL_CONFIGS = {
    "micro": "granite-4-0-h-micro-q4-k-m",
    "tiny": "granite-4-0-h-tiny-q4-k-m",
}

# Global state for running tests
current_process: Optional[subprocess.Popen] = None
stop_requested = False


class SystemGOHandler(SimpleHTTPRequestHandler):
    """HTTP request handler for System GO"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SCRIPT_DIR), **kwargs)
    
    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.debug("%s - %s", self.address_string(), format % args)
    
    def do_GET(self):
        """Handle GET requests"""
        parsed = urlparse(self.path)
        
        if parsed.path == "/" or parsed.path == "":
            # Serve the UI
            self.serve_ui()
        elif parsed.path == "/run":
            # Run tests with SSE streaming
            self.run_tests(parsed.query)
        elif parsed.path == "/stop":
            # Stop running tests
            self.stop_tests()
        elif parsed.path == "/status":
            # Get status
            self.get_status()
        elif parsed.path == "/health":
            # Health check
            self.send_json({"status": "ok"})
        else:
            # Serve static files
            super().do_GET()
    
    def serve_ui(self):
        """Serve the main UI HTML"""
        ui_path = SCRIPT_DIR / "system_go_ui.html"
        if ui_path.exists():
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(ui_path.read_bytes())
        else:
            self.send_error(404, "UI file not found")
    
    def send_json(self, data: dict):
        """Send JSON response"""
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def run_tests(self, query_string: str):
        """Execute tests and stream results via SSE"""
        global current_process, stop_requested
        
        # Parse query parameters
        params = parse_qs(query_string)
        batches = params.get("batches", ["batch1"])[0].split(",")
        model = params.get("model", ["tiny"])[0]
        assistant = params.get("assistant", ["false"])[0].lower() == "true"
        streaming = params.get("streaming", ["true"])[0].lower() == "true"
        
        # Setup SSE response
        self.send_response(200)
        self.send_header("Content-type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        
        stop_requested = False
        
        def send_event(data: dict):
            """Send an SSE event"""
            try:
                event_data = f"data: {json.dumps(data)}\n\n"
                self.wfile.write(event_data.encode())
                self.wfile.flush()
            except BrokenPipeError:
                pass
        
        try:
            # Switch model first
            send_event({"type": "log", "message": f"Switching to model: {MODEL_CONFIGS.get(model, model)}", "level": "info"})
            switch_model(model)
            
            # Build pytest command
            markers = " or ".join(batches)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            
            cmd = [
                sys.executable, "-m", "pytest",
                "rangerio_tests/integration/test_realistic_user_scenarios.py",
                "-m", markers,
                "-v",
                "--tb=short",
                f"--html={REPORTS_DIR}/run_{timestamp}.html",
                "--self-contained-html",
                "--timeout=600",
            ]
            
            # Set environment variables
            env = os.environ.copy()
            env["PYTHONPATH"] = str(SCRIPT_DIR)
            env["SYSTEM_GO_MODEL"] = model
            env["SYSTEM_GO_ASSISTANT"] = str(assistant).lower()
            env["SYSTEM_GO_STREAMING"] = str(streaming).lower()
            
            send_event({"type": "log", "message": f"Running: {' '.join(cmd)}", "level": "dim"})
            send_event({"type": "log", "message": "", "level": ""})
            
            # Start process
            current_process = subprocess.Popen(
                cmd,
                cwd=str(SCRIPT_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env
            )
            
            start_time = time.time()
            passed = 0
            failed = 0
            total_tests = len(batches) * 6  # Approximate
            current_test = 0
            
            # Stream output
            for line in iter(current_process.stdout.readline, ''):
                if stop_requested:
                    current_process.terminate()
                    send_event({"type": "log", "message": "Tests stopped by user", "level": "warning"})
                    break
                
                line = line.rstrip()
                if not line:
                    continue
                
                # Parse pytest output
                level = ""
                if "PASSED" in line:
                    level = "success"
                    passed += 1
                    current_test += 1
                    send_event({
                        "type": "result",
                        "passed": True,
                        "elapsed": time.time() - start_time
                    })
                elif "FAILED" in line:
                    level = "error"
                    failed += 1
                    current_test += 1
                    send_event({
                        "type": "result",
                        "passed": False,
                        "elapsed": time.time() - start_time
                    })
                elif "ERROR" in line:
                    level = "error"
                elif "warning" in line.lower():
                    level = "warning"
                elif line.startswith("===") or line.startswith("---"):
                    level = "info"
                elif "accuracy" in line.lower() or "score" in line.lower():
                    # Try to extract accuracy
                    import re
                    match = re.search(r'accuracy[:\s]+(\d+\.?\d*)', line.lower())
                    if match:
                        send_event({
                            "type": "result",
                            "accuracy": float(match.group(1)),
                            "elapsed": time.time() - start_time
                        })
                
                # Send log line
                send_event({"type": "log", "message": line, "level": level})
                
                # Update progress
                if total_tests > 0:
                    progress = min(100, int((current_test / total_tests) * 100))
                    send_event({"type": "progress", "percent": progress})
            
            current_process.wait()
            
            # Send completion
            elapsed = time.time() - start_time
            send_event({
                "type": "complete",
                "passed": passed,
                "failed": failed,
                "elapsed": elapsed
            })
            
        except Exception as e:
            send_event({"type": "error", "message": str(e)})
            logger.error(f"Test execution error: {e}")
        finally:
            current_process = None
    
    def stop_tests(self):
        """Stop running tests"""
        global stop_requested, current_process
        stop_requested = True
        if current_process:
            current_process.terminate()
        self.send_json({"status": "stopped"})
    
    def get_status(self):
        """Get current status"""
        import urllib.request
        import urllib.error
        
        try:
            req = urllib.request.urlopen(f"{RANGERIO_BACKEND}/health", timeout=5)
            backend_status = "connected" if req.status == 200 else "error"
        except urllib.error.URLError:
            backend_status = "offline"
        except Exception:
            backend_status = "offline"
        
        self.send_json({
            "backend": backend_status,
            "running": current_process is not None,
            "reports_dir": str(REPORTS_DIR)
        })


def switch_model(model_key: str) -> bool:
    """Switch RangerIO to use specified model"""
    import requests
    
    model_name = MODEL_CONFIGS.get(model_key, model_key)
    try:
        resp = requests.post(
            f"{RANGERIO_BACKEND}/models/{model_name}/select",
            timeout=60
        )
        if resp.ok:
            logger.info(f"Switched to model: {model_name}")
            return True
        else:
            logger.warning(f"Failed to switch model: {resp.status_code}")
    except Exception as e:
        logger.error(f"Model switch error: {e}")
    return False


def run_server():
    """Run the System GO server"""
    server = HTTPServer(("127.0.0.1", SERVER_PORT), SystemGOHandler)
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  System GO Server                                            ║
╠══════════════════════════════════════════════════════════════╣
║  UI:       http://127.0.0.1:{SERVER_PORT}                            ║
║  Reports:  {REPORTS_DIR}
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\nShutting down...")
        server.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()


if __name__ == "__main__":
    run_server()
