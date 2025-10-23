from socket import *
import os

serverPort = 12000
serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(('', serverPort))
serverSocket.listen(1)
print('The server is ready to receive')

while True:
    connectionSocket, addr = serverSocket.accept()
    print(f'Connection from {addr}')

    request = connectionSocket.recv(1024).decode()
    print("Request received:\n", request)

    try:
        request_line = request.split('\n')[0]
        method, path, version = request_line.split()
    except ValueError:
        connectionSocket.send(b"HTTP/1.1 400 Bad Request\r\n\r\n")
        connectionSocket.close()
        continue

    # Only allow GET requests for now
    if method != 'GET':
        response = "HTTP/1.1 403 Forbidden\r\n\r\n"
        connectionSocket.send(response.encode())
        connectionSocket.close()
        continue

    # Remove leading '/' from path
    filename = path.strip('/')
    if filename == '':
        filename = 'index.html'  # default file

    # File existence check
    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            body = f.read()
        response = (
            "HTTP/1.1 200 OK\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Content-Type: text/html\r\n\r\n"
        ).encode() + body
    else:
        response = "HTTP/1.1 404 Not Found\r\n\r\nFile not found".encode()

    connectionSocket.send(response)
    connectionSocket.close()
