import socket
import threading
from urllib.parse import urlparse
import time

PROXY_PORT = 12001  # Proxy server port

WEB_SERVER_HOST = "localhost"
WEB_SERVER_PORT = 12000  # Must match your MP1.py port

proxy_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
proxy_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
proxy_server.bind(('', PROXY_PORT))
proxy_server.listen(5) 
print(f"Proxy server listening on port {PROXY_PORT} ...")


def forward_request(request: str) -> bytes:
    """Forward the HTTP request to the web server and return its response."""
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

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as web_socket:
        web_socket.connect((WEB_SERVER_HOST, WEB_SERVER_PORT))
        web_socket.sendall(request.encode())

        response_chunks = []
        while True:
            chunk = web_socket.recv(4096)
            if not chunk:
                break
            response_chunks.append(chunk)
        return b"".join(response_chunks)


def handle_client(client_conn, client_addr):
    """Handle one client connection in a separate thread."""
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

        response = forward_request(request)

        client_conn.sendall(response)
        print(f"[{client_addr}] Response relayed successfully.")
    except Exception as e:
        print(f"[!] Error handling {client_addr}: {e}")
    finally:
        client_conn.close()
        print(f"[-] Connection closed: {client_addr}")


while True:
    client_conn, client_addr = proxy_server.accept()

    thread = threading.Thread(target=handle_client, args=(client_conn, client_addr))
    thread.daemon = True  
    thread.start()

    print(f"[Active Threads: {threading.active_count() - 1}]")
