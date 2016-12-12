import socket
import logging
import sys
import threading
import struct
import time
import select
from common import common

class Nocpusher(object):

    def __init__(self, config=None, mode=common.DUAL_DASHBOARD_MODE):
        if config is None:
            logging.critical("No config provided. Exiting...")
            sys.exit(2)
        self.server = None
        self.threads = []
        self.clients = []
        self.mode = mode

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
            logging.info('No port provided. Defaulting to 4455')
            self.port = 4455

        try:
            self.dashboard_frequency = int(config['dashboard_frequency'])
        except:
            logging.info('No dashboard frequency provided. Defaulting to 120s.')
            self.dashboard_frequency = 120

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
            # Wait for potential NOCDisplays that connect immediately
            time.sleep(15)
            # Loop through dashboards
            if self.mode == common.DUAL_DASHBOARD_MODE:
                for dashBoard1, dashBoard2 in zip(self.dashBoards[0::2], self.dashBoards[1::2]):
                    logging.debug("Sending DashBoard %s and %s.", dashBoard1, dashBoard2)
                    for socketFd in self.clients:
                        try:
                            dashBoards = dashBoard1 + ';' + dashBoard2
                            # Send size first so nocdisplay knows how much to receive
                            socketFd.send(struct.pack('!I', (len(dashBoards))))
                            # Now actually send the dashboards
                            socketFd.send(dashBoards)
                        except:
                            logging.info("Client %s disconnected.", socketFd)
                            socketFd.close()
                            self.clients.remove(socketFd)
                    time.sleep(self.dashboard_frequency)
            else:
                for dashBoard in self.dashBoards:
                    logging.debug("Sending DashBoard %s.", dashBoard)
                    for socketFd in self.clients:
                        try:
                            # Send size first so nocdisplay knows how much to receive
                            socketFd.send(struct.pack('!I', (len(dashBoard))))
                            # Now actually send the dashboards
                            socketFd.send(dashBoard)
                        except:
                            logging.info("Client %s disconnected.", socketFd)
                            socketFd.close()
                            self.clients.remove(socketFd)
                    time.sleep(self.dashboard_frequency)
            time.sleep(self.dashboard_frequency)



