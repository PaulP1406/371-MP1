from socket import *
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

serverPort = 12000
serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(('', serverPort))
serverSocket.listen(1)
print('The server is ready to receive')

while True:
    connectionSocket, addr = serverSocket.accept()
    
    try:
        request = connectionSocket.recv(1024).decode()
        print("Request received:\n", request)
        
        # Check if request is empty
        if not request.strip():
            print("Empty request received, closing connection")
            connectionSocket.close()
            continue
        
        # Take out the HTTP version with bounds checking
        request_line_parts = request.split('\n')[0].split()
        if len(request_line_parts) < 3:
            HTTPVersion = "HTTP/1.0"
            print("Malformed request line, defaulting to HTTP/1.0")
        else:
            HTTPVersion = request_line_parts[2]
        print("HTTP Version:", HTTPVersion)

        # Check for the 505 HTTP version not supported
        # Handle the 505 case (unsupported HTTP version)
        # Test using echo "GET /test.html HTTP/2.0`r`nHost: localhost`r`nConnection: close`r`n`r`n" | ncat localhost 12000
        if HTTPVersion not in ["HTTP/1.0", "HTTP/1.1"]:
            response = (
                "HTTP/1.1 505 HTTP Version Not Supported\r\n"
                "Content-Type: text/html\r\n"
                "\r\n"
                "<html><body><h1>505 HTTP Version Not Supported</h1>"
                "<p>The server only supports HTTP/1.0 and HTTP/1.1.</p>"
                "</body></html>"
            ).encode()
            connectionSocket.send(response)
            connectionSocket.close()
            continue

        # Handle the 200 case with bounds checking
        request_line_parts = request.split('\n')[0].split()
        if len(request_line_parts) < 2:
            # Malformed request - default to index.html
            fileName = "index.html"
            print("Malformed request line, defaulting to index.html")
        else:
            fileName = request_line_parts[1].strip('/')

        # Extract the if modified since header if its there
        if_modified_since = None
        for line in request.split('\n'):
            if line.lower().startswith("if-modified-since:"):
                try:
                    if_modified_since = parsedate_to_datetime(line.split(":", 1)[1].strip())
                    if if_modified_since.tzinfo is None:
                        if_modified_since = if_modified_since.replace(tzinfo=timezone.utc)
                    else:
                        if_modified_since = if_modified_since.astimezone(timezone.utc)
                except Exception:
                    if_modified_since = None

        if os.path.exists(fileName) and os.access(fileName, os.R_OK):
            # Get the file's last modified time (timezone-aware UTC)
            file_mtime = datetime.fromtimestamp(os.path.getmtime(fileName), tz=timezone.utc)

            # Handle the 304 case (client has cached version)
            if if_modified_since and (file_mtime - if_modified_since).total_seconds() < 3:
                response = (
                    "HTTP/1.1 304 Not Modified\r\n"
                    "Content-Type: text/html\r\n"
                    "\r\n"
                ).encode()
            else:
                try:
                    with open(fileName, 'rb') as f:
                        body = f.read()
                    response = (
                        "HTTP/1.1 200 OK\r\n"
                        "Content-Type: text/html\r\n"
                        f"Content-Length: {len(body)}\r\n"
                        f"Last-Modified: {file_mtime.strftime('%a, %d %b %Y %H:%M:%S GMT')}\r\n"
                        "\r\n"
                    ).encode() + body
                except PermissionError:
                    response = (
                        "HTTP/1.1 403 Forbidden\r\n"
                        "Content-Type: text/html\r\n"
                        "\r\n"
                        "<html><body><h1>403 Forbidden</h1><p>You do not have permission to access this file.</p></body></html>"
                    ).encode()

        # Handle the 403 case (Set the testForbidden.html permission to not accessible similar to chmod)
        elif os.path.exists(fileName) and not os.access(fileName, os.R_OK):
            response = (
                "HTTP/1.1 403 Forbidden\r\n"
                "Content-Type: text/html\r\n"
                "\r\n"
                "<html><body><h1>403 Forbidden</h1><p>You do not have permission to access this file.</p></body></html>"
            ).encode()

        # Handle the 404 case
        else:
            response = (
                "HTTP/1.1 404 Not Found\r\n"
                "Content-Type: text/html\r\n"
                "\r\n"
                "<html><body><h1>404 Not Found</h1><p>The requested file does not exist on the server.</p></body></html>"
            ).encode()

        connectionSocket.send(response)
        connectionSocket.close()
    except Exception as e:
        print(f"Error handling request from {addr}: {e}")
        try:
            connectionSocket.close()
        except:
            pass
