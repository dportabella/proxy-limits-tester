from http.server import BaseHTTPRequestHandler, HTTPServer
import time
import urllib.parse
import sys

class TestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query = urllib.parse.parse_qs(parsed_path.query)

        if path == "/timeout":
            delay = int(query.get("delay", ["0"])[0])
            print(f"[{self.client_address[0]}] Request GET /timeout?delay={delay}")
            print(f" -> Waiting {delay} seconds before answering...")
            time.sleep(delay)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(f"OK, waited {delay}s".encode())
            print(f" -> Done waiting {delay}s")

        elif path == "/download":
            size_mb = float(query.get("size_mb", ["1"])[0])
            print(f"[{self.client_address[0]}] Request GET /download?size_mb={size_mb}")
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.end_headers()
            
            chunk_size = 1024 * 1024
            total_bytes = int(size_mb * chunk_size)
            bytes_sent = 0
            
            while bytes_sent < total_bytes:
                to_send = min(chunk_size, total_bytes - bytes_sent)
                chunk = b"0" * to_send
                try:
                    self.wfile.write(chunk)
                    bytes_sent += to_send
                except Exception as e:
                    print(f" -> Connection closed by client/proxy during download: {e}")
                    break
            print(f" -> Sent {bytes_sent / (1024*1024):.2f} MB")

        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Proxy Limits Tester Server Running")

    def do_POST(self):
        parsed_path = urllib.parse.urlparse(self.path)
        if parsed_path.path == "/upload":
            content_length = int(self.headers.get('Content-Length', 0))
            print(f"[{self.client_address[0]}] Request POST /upload with Content-Length: {content_length / (1024*1024):.2f} MB")
            
            bytes_read = 0
            chunk_size = 1024 * 1024
            while bytes_read < content_length:
                read_size = min(chunk_size, content_length - bytes_read)
                data = self.rfile.read(read_size)
                if not data:
                    break
                bytes_read += len(data)
                
            print(f" -> Successfully received {bytes_read / (1024*1024):.2f} MB")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Upload successful")
        else:
            self.send_response(404)
            self.end_headers()

def run(port=10010):
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, TestHandler)
    print(f"Starting test server on 0.0.0.0:{port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
        httpd.server_close()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 10010
    run(port)
