import socket
import logging
import sys
import threading
import time
import select

class Nocpusher(object):

    def __init__(self, config=None):
        if config is None:
            logging.critical("No config provided. Exiting...")
            sys.exit(2)
        self.server = None
        self.threads = []
        self.clients = []

        try:
            if config['host'] is not None:
                self.host = config['host']
        except KeyError:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 53))
                self.host = s.getsockname()[0]
            except socket.error as msg:
                logging.critical('Unable to retrieve server\'s IP address: %s' % msg)
                sys.exit(3)

        try:
            self.dashBoards = config['dashboards']
        except:
            logging.critical('No NOC Dashboards provided. Exiting...')
            sys.exit(4)

        try:
            self.port = config['port']
        except:
            self.port = 4455

    def open_socket(self):
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind((self.host, self.port))
            self.server.listen(8)
        except socket.error, (value, message):
            if self.server:
                self.server.close()
            logging.critical( "Could not open socket: " + message)
            sys.exit(5)

    def run(self):
        logging.info("WELCOME TO THE NOCanator 3000\n")
        initMsg = "Initialized with IP " + self.host + ",port " + str(self.port) + " and the following dashboards:\n"
        for i in range(0, len(self.dashBoards)):
            initMsg += self.dashBoards[i] + "\n"
        logging.debug(initMsg)

        # Open Server Socket
        self.open_socket()

        # Inputs for this server to wait until ready for reading
        input = [self.server, sys.stdin]

        # Start the DashBoard pushing thread
        dashBoardPusherThread = threading.Thread(target=self.push_dashboards)
        dashBoardPusherThread.daemon = True
        dashBoardPusherThread.start()

        running = True
        try:
            while running:
                inputready, outputready, exceptready = select.select(input, [], [])

                for s in inputready:

                    if s == self.server:
                        # handle the server socket
                        socketFd, address = self.server.accept()
                        socketFd.settimeout(300)
                        logging.info("Received client check in for host: %s. Starting NOCDisplay there.", address)
                        self.clients.append(socketFd)

                    elif s == sys.stdin:
                        # handle standard input
                        junk = sys.stdin.readline()
                        running = False

        except KeyboardInterrupt:
            # Close all threads
            logging.info("Closing the NOCanator...")
            self.server.close()
            logging.info("All sockets closed.")
            sys.exit(6)

    def push_dashboards(self):
        while True:
            # Loop through dashboards
            for dashBoard1, dashBoard2 in zip(self.dashBoards[0::2], self.dashBoards[1::2]):
                logging.debug("Sending DashBoard %s and %s.", dashBoard1, dashBoard2)
                for socketFd in self.clients:
                    try:
                        socketFd.send(dashBoard1 + ';' + dashBoard2)
                    except:
                        logging.info("Client %s disconnected.", socketFd)
                        socketFd.close()
                        self.clients.remove(socketFd)
                time.sleep(15)



