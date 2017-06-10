from flask import Flask, request
from flask_restful import Resource, Api
import logging
import requests
import socket
import struct
import sys
import pickle
import time
import json
from common import Common
from packet import Packet
from pybrowser import Browser
import gi.repository
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit', '3.0')
from gi.repository import Gtk, WebKit, Gdk
from threading import Thread
from gi.repository import GObject

GObject.threads_init()
Gdk.threads_init()

class Nocd(object):

    def __init__(self, config_file='config.json', host=None, port=4455, profile=None, cycleFrequency=60):
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

        if host is None:
            if 'host' in self.config:
                self.host = self.config['host']
            else:
                logging.critical("FATAL: No server address specified. Exiting...")
                sys.exit(2)
        else:
            self.host = host

        self.port = int(port)

        if 'user' in self.config and 'password' in self.config:
            self.username = self.config['user']
            self.password = self.config['password']
        else:
            logging.critical("No login credentials for OKTA provided in config file. Exiting...")

        self.browser = Browser(self.username, self.password)
        self.dashboards = None
        self.num_tabs = 1
        self.client = None
        self.profile = profile
        self.cycleFrequency = cycleFrequency
        self.run_receiver_processor_thread = True
        self.run_cycle_tab_thread = True

    def init_browser(self):
        self.browser = Browser(self.username, self.password)

    def set_dashboards(self, dashboards=None):
        self.dashboards = dashboards

    def connect_to_noc_server(self):
        """
        Connects to the NOC server provided in the arguments.
        :return: Returns True if successfull and False if not.
        """
        try:
            logging.info("Attempting to connect to NOC server at {0}:{1}...".format(self.host, self.port))
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.connect((self.host, self.port))
            logging.info('Done! Connected to NOC Server.')
            return True
        except:
            logging.critical("Unable to connect to NOC server at {0}:{1}".format(self.host, self.port))
            return False

    def send_noc_profile(self):
        """
        Send a packet to the NOC server requesting NOC profile
        :return:
        """
        try:
            p = Packet(operation=Common.SEND_NOC_PROFILE, data=self.profile)
            serializedPacket = pickle.dumps(p)
            # Send size of packet first
            self.client.send(struct.pack('!I', (len(serializedPacket))))
            # Send packet
            logging.debug("Sending NOC Profile [{0}] to the NOC server at {1}".format(self.profile, self.host))
            self.client.send(serializedPacket)

            return True

        except:
            logging.critical("Failed to send NOC Profile...")
            return False

    def receive_packet(self):
        """
        Receives packet and returns content.
        :return: Returns packet content. Returns False if socket is closed.
        """
        # Receive the size of the packet first
        packetSizeByteString = self.client.recv(4)
        if packetSizeByteString == '':
            logging.debug('Connection to server closed.')
            return Packet(Common.SHUTDOWN)

        packetSize, = struct.unpack('!I', packetSizeByteString)
        # Now that we know how big the packet is going to be, we can receive it properly
        serializedPacket = self.client.recv(packetSize)
        p = pickle.loads(serializedPacket)
        logging.debug("Received packet with operation %d", p.operation)

        return p

    def receiverProcessor(self, cycleTabThread=None):
        """
        Connects to NOC server, receives and processes packets from NOC server.
        """
        while self.run_receiver_processor_thread:
            try:
                # Receive packet from NOC Server
                p = self.receive_packet()

                # Receive new list of dashboards
                if p.operation == Common.RECEIVE_DASHBOARDS:
                    self.set_dashboards(p.data)

                    # Close all opened tabs
                    for num_tabs in range(self.num_tabs - 1):
                        GObject.idle_add(self.browser.close_tab)
                        self.num_tabs -= 1

                    # Open new tabs
                    for num_tabs in range(len(self.dashboards) - self.num_tabs):
                        GObject.idle_add(self.browser.new_tab)
                        self.num_tabs += 1

                    # Open all dashboards
                    for i in range(len(self.dashboards)):
                        GObject.idle_add(self.browser.load_url_in_tab, i, self.dashboards[i])

                    logging.debug("Opened %i tabs.", self.num_tabs)

                    # Switch to first tab
                    GObject.idle_add(self.browser.reload_url_in_tab, 0, self.dashboards[0])

                    # Check if cycle tab thread is alive. If not, start it
                    if cycleTabThread.isAlive() is False:
                        cycleTabThread.start()

                elif p.operation == Common.SHUTDOWN:
                    logging.info('Shutting down receiver processor...')
                    return False

            except socket.error:
                logging.info("An error happened while receiving a packet from the NOC server. Connection \
                to NOC server was lost.")
                # Try to reconnect if connection to NOC server was lost
                while True:
                    logging.info('Reconnecting...')
                    if self.connect_to_noc_server():
                        break
                    else:
                        logging.info('Sleeping for 30 seconds...')
                        time.sleep(30)

    def cycle_tabs(self):
        """
        Cycles through the dashboards/tabs
        """
        while self.run_cycle_tab_thread:
            # Loop through dashboards-tabs
            for i in range(len(self.dashboards) - 1, -1, -1):
                time.sleep(self.cycleFrequency)
                logging.debug("Switching tabs to tab number %d: %s", i, self.dashboards[i])
                GObject.idle_add(self.browser.reload_url_in_tab, i, self.dashboards[i])

    def start_cycle_tab_thread(self):
        cycleTabThread = Thread(target=self.cycle_tabs)
        cycleTabThread.setDaemon(True)
        self.run_cycle_tab_thread = True
        cycleTabThread.start()

    def stop_cycle_tab_thread(self):
        self.run_cycle_tab_thread = False

    def open_dashboard(self, url):
        # Destroy the current browser
        del self.browser

        # Create a new browser
        self.init_browser()

        # Create new tab
        GObject.idle_add(self.browser.new_tab)

        # Open new dashboard
        GObject.idle_add(self.browser.load_url_in_tab, 0, url)

    def stop_receiver_processor_thread(self):
        self.run_receiver_processor_thread = False

    def run(self):
        logging.info("Starting NOCDisplay...")

        # Connect to NOC Server and send NOC profile
        if self.connect_to_noc_server() and self.send_noc_profile():

            # Initialize the UI
            Gtk.init(sys.argv)

            # Start the tab/dashboard cycle thread
            cycleTabThread = Thread(target=self.cycle_tabs)
            cycleTabThread.setDaemon(True)

            # Start the Receiver Processor Thread
            receiverThread = Thread(target=self.receiverProcessor, args=(cycleTabThread,))
            receiverThread.start()

            # Start the UI
            Gtk.main()

            # Close the application if GTK quit
            logging.info("Closing the application...")
            self.stop_receiver_processor_thread()
            self.client.shutdown(socket.SHUT_RDWR)
            self.client.close()
            logging.debug("Closed socket.")
            # Wait for the Receiver Thread
            logging.debug("Waiting for receiver thread to stop...")
            receiverThread.join()
            logging.debug("OK.")

        else:
            logging.critical('Unable to connect to provided NOC server...Exiting.')

        # Exit
        sys.exit(0)
