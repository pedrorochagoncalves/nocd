import socket
import logging
import sys
import threading
import struct
import time
import select
import pickle
import json
from packet import Packet
from common import Common


class Nocpusher(object):

    def __init__(self, config_file='config.json'):
        self.config_file = config_file
        # Open config file and load it into memory
        try:
            self.f = open(self.config_file)
            self.config = json.load(self.f)
            if self.config is None:
                logging.critical("No config provided. Exiting...")
                sys.exit(2)
        except IOError as msg:
            logging.critical('Cannot open config file: %s' % msg)
            sys.exit(1)

        # Configure Logging
        if 'log_level' in self.config:
            numeric_level = getattr(logging, self.config['log_level'].upper(), None)
            if not isinstance(numeric_level, int):
                raise ValueError('Invalid log level: %s' % self.config['log_level'])
            logging_level = numeric_level
        else:
            logging_level = logging.DEBUG

        if 'log_file' in self.config:
            log_file = self.config['log_file']
        else:
            log_file = '/dev/stdout'

        logging.basicConfig(level=logging_level, filename=log_file)

        if 'host' in self.config:
            self.host = self.config['host']
        else:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 53))
                self.host = s.getsockname()[0]
            except socket.error as msg:
                logging.critical('Unable to retrieve server\'s IP address: %s' % msg)
                sys.exit(3)

        if 'dashboards' in self.config:
            self.dashBoards = self.config['dashboards']
        else:
            logging.critical('No NOC Dashboards provided. Exiting...')
            sys.exit(4)

        if 'port' in self.config:
            self.port = self.config['port']
        else:
            logging.info('No port provided. Defaulting to 4455')
            self.port = 4455

        if 'dashboard_frequency' in self.config:
            self.dashboard_frequency = int(self.config['dashboard_frequency'])
        else:
            logging.info('No dashboard frequency provided. Defaulting to 120s.')
            self.dashboard_frequency = 120

        self.server = None
        self.threads = []
        self.client_socketfds = []
        self.client_addresses = []
        self.run_thread = True

    def set_dashboards(self, dashboards=None):
        self.dashBoards = dashboards

    def stop_threads(self):
        self.run_thread = False

    def reload_config(self):
        self.f.close()
        self.f = open(self.config_file)
        self.config = json.load(self.f)
        if 'dashboard_frequency' in self.config:
            self.dashboard_frequency = int(self.config['dashboard_frequency'])
        if 'dashboards' in self.config:
            self.set_dashboards(self.config['dashboards'])
            logging.info('Reloaded dashboards. New dashboards are {0}'.format(self.dashBoards))

            # Send the new dashboards to all NOCDisplays
            # logging.info('Sending the new dashboards to the NOCDisplays.')
            # for client, address in zip(self.client_socketfds, self.client_addresses):
            #    self.send_dashboards(client, address)

    def open_socket(self):
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind((self.host, self.port))
            self.server.listen(8)
        except socket.error, (value, message):
            if self.server:
                self.server.close()
            logging.critical("Could not open socket: " + message)

    def run(self):
        '''
        Run method, which starts thread to listen for new connections and thread to listen for incoming commands from
        Slack (not yet implemented).
        :return:
        '''
        logging.info("WELCOME TO THE NOCanator 3000\n")
        init_msg = 'Initialized with IP {0}, port {1} and the following dashboards:\n'.format(self.host, self.port)
        for profile in range(0, len(self.dashBoards)):
            for dashboard in self.dashBoards[profile]:
                init_msg += str(self.dashBoards[profile][dashboard]) + "\n"
        logging.debug(init_msg)

        try:
            # Start the Tab Changing thread
            tabChangerThread = threading.Thread(target=self.change_tab)
            tabChangerThread.start()

            # Start thread with loop for new connections from NOCDisplays
            newConnectionsThread = threading.Thread(target=self.new_connections)
            newConnectionsThread.start()

            while newConnectionsThread.isAlive():
                # Wait for threads to finish
                tabChangerThread.join(1)
                newConnectionsThread.join(1)

        except KeyboardInterrupt:
            self.stop_threads()
            # Wait for threads to finish
            tabChangerThread.join(1)
            newConnectionsThread.join(1)

        return 0

    def new_connections(self):
        '''
        This method handles new incoming connections from new NOCDisplays. It stores information about the new
        connections such as IP, source port, noc profile, etc.
        :return:
        '''

        # Open Server Socket
        self.open_socket()

        # Inputs for this server to wait until ready for reading
        inputs = [self.server, sys.stdin]

        while self.run_thread:
            inputready, outputready, exceptready = select.select(inputs, [], [])

            for s in inputready:

                if s == self.server:
                    # handle the server socket
                    socketFd, address = self.server.accept()
                    socketFd.settimeout(300)
                    logging.info("Received client check in for host: %s. Starting NOCDisplay there.", address)
                    self.client_socketfds.append(socketFd)
                    self.client_addresses.append(address)

                    # Receive the NOC profile from the NOCDisplay
                    nocProfile = self.receive_noc_profile(socketFd, address)

                    # Send the DashBoards to the newly joined NOCDisplay
                    self.send_dashboards(socketFd, address, nocProfile)

                elif s == sys.stdin:
                    # handle standard input
                    junk = sys.stdin.readline()
                    print "If you want to stop the server press Ctrl + C and then press return. It's stupid, I know." \
                          "You figure it, 'kay?"

        # Close the server socket
        logging.info("Closing the NOCanator...")
        self.server.close()
        logging.info("All sockets closed.")

    def receive_noc_profile(self, socketFd=None, address=None):
        '''
        Receives a packet from the NOCDisplay with the requested NOC profile
        :param socketFd:
        :param address:
        :return: NOC profile
        '''

        if socketFd is None or address is None:
            logging.critical("[FATAL] No socket and/or address passed to receive_noc_profile. Exiting...")
            sys.exit(12)

        # Receive the size of the packet first
        packetSizeByteString = socketFd.recv(4)
        packetSize, = struct.unpack('!I', packetSizeByteString)
        # Now that we know how big the packet is going to be, we can receive it properly
        serializedPacket = socketFd.recv(packetSize)
        p = pickle.loads(serializedPacket)
        logging.debug("Received NOC Profile {0} from NOC Display {0}.".format(p.data,address))

        return p.data

    def send_dashboards(self, socketFd=None, address=None, profile=None):
        '''
        Create a Packet with all the dashboards that we want the NOCDisplay to rotate.
        :return:
        '''

        if socketFd is None or address is None:
            logging.critical("[FATAL] No socket and/or address passed to send_dashboards. Exiting...")
            sys.exit(12)
        elif profile is None:
            logging.critical("[FATAL] No NOC profile provided to send_dashboards. Exiting...")
            sys.exit(13)

        # Get the requested NOC profile
        for i in range(0, len(self.dashBoards)):
            if profile in self.dashBoards[i]:
                dashBoardsToSend = self.dashBoards[i][profile]

        # Create the packet with the requested dashboards
        p = Packet(operation=Common.RECEIVE_DASHBOARDS, data=dashBoardsToSend)
        serializedPacket = pickle.dumps(p)
        # Send size of packet first
        socketFd.send(struct.pack('!I', (len(serializedPacket))))
        # Send packet
        logging.debug("Sending dashboards for profile {0} to NOCDisplay {0}".format(profile, address))
        try:
            socketFd.send(serializedPacket)
        except:
            logging.debug("Failed to send dashboards to NOCDisplay {0}. Closing client connection...".format(address))
            socketFd.close()
            self.client_socketfds.remove(socketFd)
            self.client_addresses.remove(address)

    def change_tab(self):
        '''
        Tells the NOCdisplays to change tab
        :return:
        '''
        # Wait for potential NOCDisplays that connect immediately
        time.sleep(15)

        while self.run_thread:
            # Loop through dashboards-tabs
            for i in range(len(self.dashBoards)-1, -1, -1):
                time.sleep(self.dashboard_frequency)
                # Loop through the current list of NOCDisplays
                for client, address in zip(self.client_socketfds, self.client_addresses):
                    try:
                        p = Packet(operation=Common.SWITCH_TAB, data=i)
                        serializedPacket = pickle.dumps(p)
                        # Send size of packet first
                        client.send(struct.pack('!I', (len(serializedPacket))))
                        # Send packet
                        logging.debug("Telling NOCDisplays to switch to tab %d", i)
                        client.send(serializedPacket)
                    except:
                        logging.info("Client %s disconnected.", address)
                        client.close()
                        self.client_socketfds.remove(client)
                        self.client_addresses.remove(address)

