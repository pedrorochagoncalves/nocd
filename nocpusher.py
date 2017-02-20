import socket
import logging
import sys
import threading
import struct
import time
import select
import pickle
from packet import Packet
from common import Common


class Nocpusher(object):

    def __init__(self, config=None):
        if config is None:
            logging.critical("No config provided. Exiting...")
            sys.exit(2)
        self.server = None
        self.threads = []
        self.clients = []

        if 'host' in config:
             self.host = config['host']
        else:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 53))
                self.host = s.getsockname()[0]
            except socket.error as msg:
                logging.critical('Unable to retrieve server\'s IP address: %s' % msg)
                sys.exit(3)

        if 'dashboards' in config:
            self.dashBoards = config['dashboards']
        else:
            logging.critical('No NOC Dashboards provided. Exiting...')
            sys.exit(4)

        if 'port' in config:
            self.port = config['port']
        else:
            logging.info('No port provided. Defaulting to 4455')
            self.port = 4455

        if 'dashboard_frequency' in config:
            self.dashboard_frequency = int(config['dashboard_frequency'])
        else:
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
            logging.critical("Could not open socket: " + message)
            sys.exit(5)

    def run(self):
        logging.info("WELCOME TO THE NOCanator 3000\n")
        init_msg = 'Initialized with IP {0}, port {1} and the following dashboards:\n'.format(self.host, self.port)
        for i in range(0, len(self.dashBoards)):
            init_msg += self.dashBoards[i] + "\n"
        logging.debug(init_msg)

        # Open Server Socket
        self.open_socket()

        # Inputs for this server to wait until ready for reading
        input = [self.server, sys.stdin]

        # Start the Tab Changing thread
        tabChangerThread = threading.Thread(target=self.change_tab)
        tabChangerThread.daemon = True
        tabChangerThread.start()

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

                        # Send the DashBoards to the newly joined NOCDisplay
                        self.send_dashboards(socketFd, address)

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

    def send_dashboards(self, socketFd=None, address=None):
        '''
        Create a Packet with all the dashboards that we want the NOCDisplay to rotate.
        :return:
        '''

        if socketFd is None or address is None:
            logging.critical("[FATAL] No socket and/or address passed to send_dashboards. Exiting...")
            sys.exit(12)
        p = Packet(operation=Common.RECEIVE_DASHBOARDS,data=self.dashBoards)
        serializedPacket = pickle.dumps(p)
        # Send size of packet first
        socketFd.send(struct.pack('!I', (len(serializedPacket))))
        # Send packet
        logging.debug("Sending dashboard list to %s", address)
        socketFd.send(serializedPacket)

    def change_tab(self):
        '''
        Tells the NOCdisplays to change tab
        :return:
        '''
        # Wait for potential NOCDisplays that connect immediately
        time.sleep(15)

        while True:
            # Loop through dashboards-tabs
            for i in range(len(self.dashBoards)):
                time.sleep(self.dashboard_frequency)
                # Loop through the current list of NOCDisplays
                for client in self.clients:
                    try:
                        p = Packet(operation=Common.SWITCH_TAB, data=i)
                        serializedPacket = pickle.dumps(p)
                        # Send size of packet first
                        client.send(struct.pack('!I', (len(serializedPacket))))
                        # Send packet
                        logging.debug("Telling NOCDisplays to switch to tab %d", i)
                        client.send(serializedPacket)
                    except:
                        logging.info("Client %s disconnected.", client)
                        client.close()
                        self.clients.remove(client)

