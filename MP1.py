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

    request = connectionSocket.recv(1024).decode()
    print("Request received:\n", request)

    # Handle the 200 case
    fileName = request.split('\n')[0].split()[1].strip('/')

    # Extract "If-Modified-Since" header if present
    if_modified_since = None
    for line in request.split('\n'):
        if line.lower().startswith("if-modified-since:"):
            try:
                if_modified_since = parsedate_to_datetime(line.split(":", 1)[1].strip())
                # Ensure timezone-aware in UTC
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
