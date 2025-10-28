import socket
import threading
from urllib.parse import urlparse
import time
import queue
import struct
import json

# configs
PROXY_PORT = 12001 
WEB_SERVER_HOST = "localhost"
WEB_SERVER_PORT = 12000  # this is just to match the MP1.py port 

FRAME_SIZE = 1024 
MAX_FRAMES_PER_REQUEST = 100 

# HOL blocking section
class Frame:
    def __init__(self, frame_id, request_id, data, is_last=False):
        self.frame_id = frame_id
        self.request_id = request_id
        self.data = data
        self.is_last = is_last
        self.timestamp = time.time()

class FrameMultiplexer:
    def __init__(self):
        self.frame_queue = queue.PriorityQueue()
        self.active_requests = {}  
        self.request_frames = {}
        self.frame_lock = threading.Lock()
        self.next_request_id = 0
        
    def add_request(self, client_conn, client_addr, request_data):
        with self.frame_lock:
            request_id = self.next_request_id
            self.next_request_id += 1
            
        self.active_requests[request_id] = (client_conn, client_addr)
        self.request_frames[request_id] = []
        
        frames = self._split_into_frames(request_id, request_data)
  
        for i, frame in enumerate(frames):
            priority = (request_id, i)
            self.frame_queue.put((priority, frame))
            
        print(f"Request {request_id} split into {len(frames)} frames")
        return request_id
    
    def _split_into_frames(self, request_id, data):
        frames = []
        data_bytes = data.encode() if isinstance(data, str) else data
        
        for i in range(0, len(data_bytes), FRAME_SIZE):
            frame_data = data_bytes[i:i + FRAME_SIZE]
            is_last = (i + FRAME_SIZE >= len(data_bytes))
            frame = Frame(i // FRAME_SIZE, request_id, frame_data, is_last)
            frames.append(frame)
            
        return frames
    
    def process_frames(self):
        while True:
            try:
                priority, frame = self.frame_queue.get(timeout=1)

                response_frames = self._forward_frame_to_server(frame)

                self._reassemble_and_send_response(frame.request_id, response_frames)
                
                self.frame_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error processing frame: {e}")
    
    def _forward_frame_to_server(self, frame):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as web_socket:
                web_socket.connect((WEB_SERVER_HOST, WEB_SERVER_PORT))
                web_socket.sendall(frame.data)
                response_frames = []
                while True:
                    chunk = web_socket.recv(FRAME_SIZE)
                    if not chunk:
                        break
                    response_frames.append(chunk)
                    
                return response_frames
                
        except Exception as e:
            print(f"Error forwarding frame {frame.frame_id}: {e}")
            return [b"HTTP/1.1 500 Internal Server Error\r\n\r\n"]
    
    def _reassemble_and_send_response(self, request_id, response_frames):
        try:
            if request_id not in self.active_requests:
                return
                
            client_conn, client_addr = self.active_requests[request_id]            
            full_response = b"".join(response_frames)
            
            client_conn.sendall(full_response)
            print(f"Response sent to {client_addr} for request {request_id}")
            del self.active_requests[request_id]
            del self.request_frames[request_id]
            client_conn.close()
            
        except Exception as e:
            print(f"Error sending response for request {request_id}: {e}")
frame_multiplexer = FrameMultiplexer()

frame_processor = threading.Thread(target=frame_multiplexer.process_frames)
frame_processor.daemon = True
frame_processor.start()

proxy_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
proxy_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
proxy_server.bind(('', PROXY_PORT))
proxy_server.listen(5)  # backlog increased for concurrency
print(f"Proxy server listening on port {PROXY_PORT} with frame-based multiplexing...")


# old code for cases before HOL blocking implementation

# def forward_request(request: str) -> bytes:
#     """Forward the HTTP request to the web server and return its response."""
#     # --- Fix the request line if it includes the full URL ---
#     lines = request.split('\r\n')
#     if lines:
#         parts = lines[0].split()
#         if len(parts) >= 2:
#             # Example: "GET http://localhost:12000/test.html HTTP/1.1"
#             url = parts[1]
#             parsed = urlparse(url)
#             if parsed.path:  # replace with just "/test.html"
#                 parts[1] = parsed.path
#                 if parsed.query:
#                     parts[1] += "?" + parsed.query
#                 lines[0] = " ".join(parts)
#                 request = "\r\n".join(lines)
# 
#     # Connect to the destination web server
#     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as web_socket:
#         web_socket.connect((WEB_SERVER_HOST, WEB_SERVER_PORT))
#         web_socket.sendall(request.encode())
# 
#         # Collect the entire response
#         response_chunks = []
#         while True:
#             chunk = web_socket.recv(4096)
#             if not chunk:
#                 break
#             response_chunks.append(chunk)
#         return b"".join(response_chunks)
# 
# 
# def handle_client(client_conn, client_addr):
#     """Handle one client connection in a separate thread."""
#     print(f"\n[+] New connection from {client_addr}")
#     time.sleep(5)
#     try:
#         request_bytes = client_conn.recv(4096)
#         if not request_bytes:
#             client_conn.close()
#             return
# 
#         # Decode safely
#         try:
#             request = request_bytes.decode()
#         except UnicodeDecodeError:
#             request = request_bytes.decode("latin-1")
# 
#         print(f"[{client_addr}] Request line: {request.splitlines()[0] if request else ''}")
# 
#         # Forward to web server and get response
#         response = forward_request(request)
# 
#         # Send response back to client
#         client_conn.sendall(response)
#         print(f"[{client_addr}] Response relayed successfully.")
#     except Exception as e:
#         print(f"[!] Error handling {client_addr}: {e}")
#     finally:
#         client_conn.close()
#         print(f"[-] Connection closed: {client_addr}")


def handle_client_frame_based(client_conn, client_addr):
    print(f"\n[+] New connection from {client_addr}")
    time.sleep(5)
    
    try:
        request_bytes = client_conn.recv(4096)
        if not request_bytes:
            client_conn.close()
            return

        try:
            request = request_bytes.decode()
        except UnicodeDecodeError:
            request = request_bytes.decode("latin-1")

        print(f"[{client_addr}] Request line: {request.splitlines()[0] if request else ''}")
        lines = request.split('\r\n')
        if lines:
            parts = lines[0].split()
            if len(parts) >= 2:
                url = parts[1]
                parsed = urlparse(url)
                if parsed.path:
                    parts[1] = parsed.path
                    if parsed.query:
                        parts[1] += "?" + parsed.query
                    lines[0] = " ".join(parts)
                    request = "\r\n".join(lines)

        request_id = frame_multiplexer.add_request(client_conn, client_addr, request)
        print(f"[{client_addr}] Request {request_id} added to frame multiplexer")
        
    except Exception as e:
        print(f"[!] Error handling {client_addr}: {e}")
        try:
            client_conn.close()
        except:
            pass

# main proxy loop
while True:
    client_conn, client_addr = proxy_server.accept()

    # Create and start a new thread for each client
    thread = threading.Thread(target=handle_client_frame_based, args=(client_conn, client_addr))
    thread.daemon = True  # ensures threads exit when main program exits
    thread.start()

    print(f"[Active Threads: {threading.active_count() - 1}]")
