import socket
from urllib.parse import urlparse

# Proxy configuration
PROXY_PORT = 12001  # Proxy server port

# Destination web server (your webserver.py)
WEB_SERVER_HOST = "localhost"
WEB_SERVER_PORT = 12000  # Must match your webserver.py port

# Create proxy server socket
proxy_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
proxy_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
proxy_server.bind(('', PROXY_PORT))
proxy_server.listen(1)
print(f"Proxy server listening on port {PROXY_PORT} ...")

def forward_request(request: str) -> bytes:
    """Forward the HTTP request to the web server and return its response."""
    print("Forwarding request to local web server...")

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

# --- Main Proxy Loop ---
while True:
    client_conn, client_addr = proxy_server.accept()
    print(f"\nConnection from {client_addr}")

    try:
        request_bytes = client_conn.recv(4096)
        if not request_bytes:
            client_conn.close()
            continue

        # Decode safely
        try:
            request = request_bytes.decode()
        except UnicodeDecodeError:
            request = request_bytes.decode("latin-1")

        print("Request line:", request.splitlines()[0] if request else "")
        response = forward_request(request)

        # Send the web server's response back to the client
        client_conn.sendall(response)
    except Exception as e:
        print("Error:", e)
    finally:
        client_conn.close()
