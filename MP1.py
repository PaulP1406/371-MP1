from socket import *
import os
from datetime import datetime
from email.utils import formatdate

serverPort = 12000
serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(('', serverPort))
serverSocket.listen(1)
print('The server is ready to receive')

while True:
    print("Waiting for a new connection...")
    connectionSocket, addr = serverSocket.accept()
    print(f'Connection established with {addr}')

    request = connectionSocket.recv(1024).decode()
    print("Request received:\n", request)

    try:
        request_line = request.split('\n')[0]
        method, path, version = request_line.split()
    except ValueError:
        print("Status code: 400")
        connectionSocket.send(b"HTTP/1.1 400 Bad Request\r\n\r\n")
        connectionSocket.close()
        continue

    # Only allow GET requests for now
    if method != 'GET':
        print("Status code: 403")
        response = (
            "HTTP/1.1 403 Forbidden\r\n"
            "Content-Type: text/html\r\n"
            "Connection: close\r\n\r\n"
            "<html><body><h1>403 Forbidden</h1></body></html>"
        )
        connectionSocket.send(response.encode())
        connectionSocket.close()
        continue

    # Remove leading '/' from path
    filename = path.strip('/')
    if filename == '':
        filename = 'index.html'  # default file
    
    # Enforce 403 Forbidden for files with "secret" in the filename
    if "secret" in filename:
        print("Status code: 403")
        response = (
            "HTTP/1.1 403 Forbidden\r\n"
            "Content-Type: text/html\r\n"
            "Connection: close\r\n\r\n"
            "<html><body><h1>403 Forbidden</h1></body></html>"
        )
        connectionSocket.send(response.encode())
        connectionSocket.close()
        continue

    # File existence check
    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            body = f.read()
        response = (
            "HTTP/1.1 200 OK\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Content-Type: text/html\r\n"
            f"Last-Modified: {formatdate(os.path.getmtime(filename), usegmt=True)}\r\n"
            "Connection: close\r\n\r\n"
        ).encode() + body
        print("Status code: 200")
    else:
        print("Status code: 404")
        response = (
            "HTTP/1.1 404 Not Found\r\n"
            "Content-Type: text/html\r\n"
            "Connection: close\r\n\r\n"
            "<html><body><h1>404 Not Found</h1></body></html>"
        ).encode()

    connectionSocket.send(response)
    connectionSocket.close()
