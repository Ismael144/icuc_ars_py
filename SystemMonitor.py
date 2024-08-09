import socket
import json
import threading
from Logger import Logger
import time
import socketserver

class SystemMonitor:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
        self.logger = Logger()

    def connect(self):
        while True:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.host, self.port))
                print(f"Connected to server at {self.host}:{self.port}")
                break
            except (ConnectionRefusedError, OSError) as e:
                print(f"Connection failed: {e}")
                print("Retrying in 2 seconds...")
                time.sleep(2)

    def send_and_receive(self, message):
        try:
            self.sock.sendall(message.encode())
            return self.sock.recv(1024).decode()
        except OSError as e:
            print(f"Error sending/receiving data: {e}")
            self.close()
            return ""

    def establish_connection(self):
        response = self.send_and_receive("PING")
        if response.strip() != "PONG":
            print("Failed to establish connection with server")
            return False
        print("Connection established with server")
        return True

    def send_json(self, message):
        try:
            json.loads(message)  # Validate JSON
            response = self.send_and_receive(message)
            print(f"Received from server: {response}")
        except json.JSONDecodeError:
            print("Invalid JSON. Please enter a valid JSON message.")

    def close(self):
        if self.sock:
            try:
                self.sock.close()
                print("Connection closed")
            except OSError as e:
                print(f"Error closing socket: {e}")

    def run(self):
        self.connect()
        stats = {}
        if not self.establish_connection():
            return

        try:
            while True:
                time.sleep(3)
                logger_content = self.logger.read()
                stats["logs"] = logger_content.split("\n")
                self.send_json(json.dumps(stats))
        except KeyboardInterrupt:
            print("Stopping client...")
        finally:
            self.close()


class ClientHandler(socketserver.BaseRequestHandler):
    def handle(self):
        print(f"Connected by {self.client_address}")
        while True:
            try:
                data = self.request.recv(1024).decode()
                if not data:
                    break
                print(f"Received from {self.client_address}: {data}")
                self.request.sendall(data.encode())
            except OSError as e:
                print(f"Error during client communication: {e}")
                break


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True


def run_server(host, port):
    server = ThreadedTCPServer((host, port), ClientHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    print(f"Server running on {host}:{port}")
    return server


if __name__ == "__main__":
    HOST, PORT = 'localhost', 8080

    # Start the server in a separate thread
    server = run_server(HOST, PORT)

    # Run the client
    client = SystemMonitor(HOST, PORT)
    client.run()

    # Shutdown the server
    print("Shutting down the server...")
    server.shutdown()
    server.server_close()
