import logging
import random
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
        self.run_cycle_tab_thread = True
        self.cycle_tab_thread = None
        self.bind_window = None

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
        try:
            # Receive the size of the packet first
            packetSizeByteString = self.client.recv(4)
            packetSize, = struct.unpack('!I', packetSizeByteString)
            # Now that we know how big the packet is going to be, we can receive it properly
            serializedPacket = self.client.recv(packetSize)
            p = pickle.loads(serializedPacket)
            logging.debug("Received packet with operation %d", p.operation)

            # Close socket to NOC server
            self.client.shutdown(socket.SHUT_RDWR)
            self.client.close()

            return p

        except socket.error:
            logging.info("An error happened while receiving a packet from the NOC server. Please try again.")
            self.client.close()
            return False


    def receive_dashboards(self):
        """
        Receive dashboards from NOCpusher.
        """
        try:
            # Receive packet from NOC Server
            p = self.receive_packet()

            # Skip there's an error
            if p is False:
                raise socket.error

            # Receive new list of dashboards
            if p.operation == Common.RECEIVE_DASHBOARDS:
                if self.dashboards:
                    del self.dashboards[:]
                self.set_dashboards(p.data)

                # Close all opened tabs
                for num_tabs in range(self.num_tabs):
                    if self.num_tabs == 1:
                        break
                    GObject.idle_add(self.browser.close_tab)
                    self.num_tabs -= 1

                # Open new tabs
                for num_tabs in range(len(self.dashboards) - 1):
                    GObject.idle_add(self.browser.new_tab)
                    self.num_tabs += 1

                # Open all dashboards
                for i in range(len(self.dashboards)):
                    logging.debug("Opening {0} {1}.".format(self.dashboards[i], i))
                    GObject.idle_add(self.browser.load_url_in_tab, i, self.dashboards[i])

                logging.debug("Opened %i tabs.", self.num_tabs)

                # Success
                return True

            elif p.operation == Common.SHUTDOWN:
                logging.info('Shutting down receiver processor...')
                return False

        except socket.error:
            logging.info("An error happened while receiving a packet from the NOC server.")
            return False


    def cycle_tabs(self):
        """
        Cycles through the dashboards/tabs
        """
        while self.run_cycle_tab_thread:
            # Loop through dashboards-tabs
            for i in range(len(self.dashboards) - 1, -1, -1):
                for j in range(int(self.cycleFrequency)):
                    time.sleep(1)
                    if not self.run_cycle_tab_thread:
                        break
                logging.debug("Switching tabs to tab number %d: %s", i, self.dashboards[i])
                GObject.idle_add(self.browser.reload_url_in_tab, i, self.dashboards[i])

    def start_cycle_tab_thread(self):
        self.cycle_tab_thread = Thread(target=self.cycle_tabs)
        self.cycle_tab_thread.setDaemon(True)
        self.run_cycle_tab_thread = True
        self.cycle_tab_thread.start()

    def stop_cycle_tab_thread(self):
        self.run_cycle_tab_thread = False

    def clear_all_and_open_new_dashboard(self, url):

        # Stop cycling dashboards
        self.stop_cycle_tab_thread()
        self.cycle_tab_thread.join()

        # Close all tabs except first one
        for num_tabs in range(self.num_tabs-1):
            if self.num_tabs == 1:
                break
            GObject.idle_add(self.browser.close_tab)
            self.num_tabs -= 1
        del self.dashboards[:]

        # Open new dashboard
        GObject.idle_add(self.browser.load_url_in_tab, 0, url)
        # Add it to the list of dashboards
        self.dashboards.append(url)

        # Start cycling dashboards
        self.start_cycle_tab_thread()

    def add_dashboard(self, url):

        # Stop cycling dashboards
        self.stop_cycle_tab_thread()
        self.cycle_tab_thread.join()

        # Open new tab
        GObject.idle_add(self.browser.new_tab)
        self.num_tabs += 1

        # Load dashboard
        GObject.idle_add(self.browser.load_url_in_tab, self.num_tabs-1, url)
        # Add it to the list of dashboards
        self.dashboards.append(url)

        # Start cycling dashboards
        self.start_cycle_tab_thread()

    def close_tab(self, tab_index):

        # Check if index exists
        if tab_index+1 > self.num_tabs:
            return False
        # Check if last tab
        if tab_index == -1:
            tab_index = self.num_tabs - 1

        # Stop cycling dashboards
        self.stop_cycle_tab_thread()
        self.cycle_tab_thread.join()

        # Close tab
        GObject.idle_add(self.browser.close_tab, tab_index)
        self.num_tabs -= 1
        # Remove it from the list of dashboards
        del(self.dashboards[tab_index])

        # Start cycling dashboards
        self.start_cycle_tab_thread()

    def create_bind_window(self):
        """
        Creates a GTK window with a random int to bind a user to a NOCd instance
        :return: the random generated int
        """
        bind_number = random.randint(1, 10000)
        self.bind_window = Gtk.Window()
        label = Gtk.Label("<span size=\"400000\">" + str(bind_number) + "</span>")
        label.set_use_markup(True)
        self.bind_window.add(label)
        GObject.idle_add(self.bind_window.show_all)

        return bind_number

    def destroy_bind_window(self):
        """
        Destroys the GTK window created to show a random int and bind a user to a NOCd instance
        :return:
        """
        GObject.idle_add(self.bind_window.destroy)

    def open_dashboards_for_profile(self, profile=None):
        """
        Connects to the NOC server, sends the NOC profile and receives the dashboards
        :return: True if dashboards are received, False if not
        """
        if profile:
            self.profile = profile

        # Connect to NOC server
        if self.connect_to_noc_server():

            # Send NOC profile
            if self.send_noc_profile():

                # Receive dashboards
                if self.receive_dashboards():
                    return True
                else:
                    return False
            else:
                return False
        else:
            return False

    def run(self):
        logging.info("Starting NOCDisplay...")

        # Connect to NOC Server and send NOC profile
        if self.open_dashboards_for_profile():

            # Initialize the UI
            Gtk.init(sys.argv)

            # Start the tab/dashboard cycle thread
            self.start_cycle_tab_thread()

            # Start the UI
            Gtk.main()

            # Close the application if GTK quit
            logging.info("Closing the application...")
            logging.debug("Closed socket.")
            # Wait for the Receiver Thread
            logging.debug("OK.")

        else:
            logging.critical('Failed to open dashboards for the provided profile...Exiting.')

        # Exit
        sys.exit(0)
