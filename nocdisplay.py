import logging
import socket

class Nocdisplay(object):

    def __init__(self, host=None, port=4455):
        if host is None:
            logging.critical("No server address specified. Exiting...")
            exit(2)
        else:
            self.host = host

        self.port = int(port)
        self.client = None

    def run(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((self.host, self.port))

        running = True
        while running:
            try:
                dashBoard = self.client.recv(128)
                print(dashBoard)
            except KeyboardInterrupt:
                self.client.close()
                exit(3)
