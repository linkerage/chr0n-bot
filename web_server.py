#!/usr/bin/env python3
"""
Simple web server for Replit keep-alive pings
Runs alongside the IRC bot to keep the Repl alive
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import json
from datetime import datetime

class PingHandler(BaseHTTPRequestHandler):
    """Handle HTTP requests for keep-alive pings"""
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/':
            # Main status page
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            status = {
                'status': 'online',
                'bot': 'chr0n-bot',
                'timestamp': datetime.utcnow().isoformat(),
                'message': 'IRC Bot is running! 🌿'
            }
            
            self.wfile.write(json.dumps(status, indent=2).encode())
            
        elif self.path == '/ping':
            # Simple ping endpoint
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'pong')
            
        elif self.path == '/health':
            # Health check endpoint
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            health = {
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.wfile.write(json.dumps(health).encode())
            
        else:
            # 404 for other paths
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def log_message(self, format, *args):
        """Suppress default logging (optional - remove this to see logs)"""
        pass


class WebServer:
    """Web server that runs in a background thread"""
    
    def __init__(self, port=8080):
        self.port = port
        self.server = None
        self.thread = None
        
    def start(self):
        """Start the web server in a background thread"""
        self.server = HTTPServer(('0.0.0.0', self.port), PingHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        print(f"Web server started on port {self.port}")
        
    def stop(self):
        """Stop the web server"""
        if self.server:
            self.server.shutdown()
            print("Web server stopped")


if __name__ == "__main__":
    # Test the server standalone
    server = WebServer(8080)
    server.start()
    print("Web server running. Press Ctrl+C to stop.")
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
        print("\nServer stopped.")
