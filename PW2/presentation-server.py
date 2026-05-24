import http.server
import socketserver
import subprocess

PORT = 5000

class MakeHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/run-demo':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            # This HTML tells the browser tab to instantly close itself
            html = "<script>window.close();</script>"
            self.wfile.write(html.encode('utf-8'))
            
            print("Received click from Slides. Running 'make phase3'...")
            subprocess.Popen(["make", "phase3"]) 
            
        else:
            self.send_response(404)
            self.end_headers()
            
socketserver.TCPServer.allow_reuse_address = True

with socketserver.TCPServer(("", PORT), MakeHandler) as httpd:
    print(f"Server is running on port {PORT}...")
    print(f"Clicking the link in Slides will open a tab that instantly closes itself.")
    httpd.serve_forever()