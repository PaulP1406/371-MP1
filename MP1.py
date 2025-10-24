from socket import *
import os

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
    if os.path.exists(fileName) and os.access(fileName, os.R_OK):
        try:
            with open(fileName, 'rb') as f:
                body = f.read()
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/html\r\n\r\n"
                f"Content-Length: {len(body)}\r\n"
            ).encode() + body
        except PermissionError:
            # In case access changes while reading, send 403 instead of crashing
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
