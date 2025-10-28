import socket
import threading
from urllib.parse import urlparse
import time

# Proxy configuration
PROXY_PORT = 12001  # Proxy server port

# Destination web server (your webserver.py)
WEB_SERVER_HOST = "localhost"
WEB_SERVER_PORT = 12000  # Must match your webserver.py port

# Create proxy server socket
proxy_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
proxy_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
proxy_server.bind(('', PROXY_PORT))
proxy_server.listen(5)  # backlog increased for concurrency
print(f"Proxy server listening on port {PROXY_PORT} ...")


def forward_request(request: str) -> bytes:
    """Forward the HTTP request to the web server and return its response."""
    # --- Fix the request line if it includes the full URL ---
    lines = request.split('\r\n')
    if lines:
        parts = lines[0].split()
        if len(parts) >= 2:
            # Example: "GET http://localhost:12000/test.html HTTP/1.1"
            url = parts[1]
            parsed = urlparse(url)
            if parsed.path:  # replace with just "/test.html"
                parts[1] = parsed.path
                if parsed.query:
                    parts[1] += "?" + parsed.query
                lines[0] = " ".join(parts)
                request = "\r\n".join(lines)

    # Connect to the destination web server
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as web_socket:
        web_socket.connect((WEB_SERVER_HOST, WEB_SERVER_PORT))
        web_socket.sendall(request.encode())

        # Collect the entire response
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

        # Decode safely
        try:
            request = request_bytes.decode()
        except UnicodeDecodeError:
            request = request_bytes.decode("latin-1")

        print(f"[{client_addr}] Request line: {request.splitlines()[0] if request else ''}")

        # Forward to web server and get response
        response = forward_request(request)

        # Send response back to client
        client_conn.sendall(response)
        print(f"[{client_addr}] Response relayed successfully.")
    except Exception as e:
        print(f"[!] Error handling {client_addr}: {e}")
    finally:
        client_conn.close()
        print(f"[-] Connection closed: {client_addr}")


# --- Main Proxy Loop (Multithreaded) ---
while True:
    client_conn, client_addr = proxy_server.accept()

    # Create and start a new thread for each client
    thread = threading.Thread(target=handle_client, args=(client_conn, client_addr))
    thread.daemon = True  # ensures threads exit when main program exits
    thread.start()

    print(f"[Active Threads: {threading.active_count() - 1}]")
