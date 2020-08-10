
import socket


class Client:

    def __init__(self, host, port, timeout, bsize):

        # network client configuration
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connection.connect((host, port))
        self.connection.settimeout(timeout)
        self.bsize = bsize
        print("\n[*] Connected to server...")

    def send(self, msg):
        self.connection.send(msg)

    def recv(self):
        return self.connection.recv(self.bsize)

    def close(self):
        self.connection.close()

    def settimeout(self, timeout):
        self.connection.settimeout(timeout)


class Server:

    def __init__(self, host, port, timeout, bsize):
        backlog = 1
        self.bsize = bsize
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind((host, port))
        self.s.listen(backlog)

    def send(self, msg):
        self.connection.send(msg)
        #print "[*] Sent msg:\n{}".format(msg)

    def recv(self):
        msg = self.connection.recv(self.bsize)
        #print "[*] Received msg:\n{}".format(msg)
        return msg

    def close(self):
        self.connection.close()

    def accept(self):
        print("\n[ ] Waiting for client connection...")
        self.connection, self.address = self.s.accept()
        print("[*] Connected to client...")

    def settimeout(self, timeout):
        self.connection.settimeout(timeout)
