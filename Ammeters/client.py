from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR


def request_current_from_ammeter(port: int, command: bytes):
    with socket(AF_INET, SOCK_STREAM) as s:
        s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        s.settimeout(5.0)
        s.connect(('127.0.0.1', port))
        s.sendall(command)
        data = s.recv(1024)
        if data:
            print(f"Received current measurement from port {port}: {data.decode('utf-8')} A")
        else:
            print("No data received.")

