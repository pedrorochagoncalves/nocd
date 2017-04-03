import logging
import socket
import struct
import sys
import pickle
import time
import json
from common import Common
from pybrowser import Browser
import gi.repository
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit', '3.0')
from gi.repository import Gtk, WebKit
from threading import Thread
from gi.repository import GObject


class Nocdisplay(object):

    def __init__(self, config_file='config.json', host=None, port=4455):
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
            self.user = self.config['user']
            self.password = self.config['password']

        else:
            logging.critical("No login credentials for OKTA provided in config file. Exiting...")

        self.dashboards = None
        self.num_tabs = 1
        self.client = None

    def set_dashboards(self, dashboards=None):
        self.dashBoards = dashboards

    def receiverProcessor(self, browser):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((self.host, self.port))

        running = True
        while running:
            try:
                # Receive the size of the packet first
                packetSizeByteString = self.client.recv(4)
                packetSize, = struct.unpack('!I', packetSizeByteString)
                # Now t hat we know how big the packet is going to be, we can receive it properly
                serializedPacket = self.client.recv(packetSize)
                p = pickle.loads(serializedPacket)
                logging.debug("Received packet with operation %d", p.operation)

                # Receive new list of dashboards
                if p.operation == Common.RECEIVE_DASHBOARDS:
                    self.set_dashboards(p.data)
                    # Open the necessary number of tabs
                    #if self.num_tabs < len(self.dashBoards):
                    #    for num_tabs in range(len(self.dashBoards) - self.num_tabs):
                    #        self.do_thread_work(self.new_tab, browser)
                    #        self.num_tabs += 1
                    #else:
                    #    for num_tabs in range(self.num_tabs - len(self.dashBoards)):
                    #        self.do_thread_work(self.close_tab, browser)

                    # Close all opened tabs
                    for num_tabs in range(self.num_tabs - 1):
                        self.do_thread_work(self.close_tab, browser)
                        self.num_tabs -= 1

                    # Open new tabs
                    for num_tabs in range(len(self.dashBoards) - self.num_tabs):
                        self.do_thread_work(self.new_tab, browser)
                        self.num_tabs += 1

                    # Open all dashboards
                    for i in range(len(self.dashBoards)):
                        self.do_thread_work(self.load_url_in_tab, browser, i, self.dashBoards[i])

                    logging.debug("Opened %i tabs.", self.num_tabs)

                    # Switch to first tab
                    self.do_thread_work(self.reload_and_focus_tab, browser, 0)

                elif p.operation == Common.SWITCH_TAB:
                    logging.debug("Switching window to %d: %s", p.data, self.dashBoards[p.data])
                    self.do_thread_work(self.reload_and_focus_tab, browser, p.data)

            except:
                sys.exit(3)

    def load_url_in_tab(self, browser, tabIndex, url):
        browser.tabs[tabIndex][0].load_url(url)
        self.okta_login(browser, tabIndex)

    def new_tab(self, browser):
        browser.open_new_tab()

    def close_tab(self, browser):
        browser.close_current_tab()

    def reload_and_focus_tab(self, browser, tabIndex):
        browser.reload_tab(tabIndex)
        # This doesn't seem to work, the load status never changes
        # while browser.tabs[tabIndex][0].webview.get_load_status() != WebKit.LoadStatus.WEBKIT_LOAD_FINISHED:
        time.sleep(5)
        self.okta_login(browser, tabIndex)
        browser.notebook.set_current_page(tabIndex)

    def okta_login(self, browser, tabIndex):
        doc = browser.tabs[tabIndex][0].get_html()
        if 'user-signin' in doc and 'pass-signin' in doc:
            logging.debug('OKTA login found')
            browser.tabs[tabIndex][0].webview.execute_script("document.getElementById('user-signin').value='{0}';".format(self.user))
            browser.tabs[tabIndex][0].webview.execute_script("document.getElementById('pass-signin').value='{0}';".format(self.password))
            browser.tabs[tabIndex][0].webview.execute_script("document.getElementById('credentials').submit();")
        else:
            logging.debug('OKTA login not found')

    def do_thread_work(self, function, *args):
        GObject.idle_add(function, *args)

    def run(self):
        logging.info("Starting NOCDisplay...")

        # Create the Browser
        Gtk.init(sys.argv)
        browser = Browser()

        # Start the Receiver Processor Thread
        receiverThread = Thread(target=self.receiverProcessor, args=(browser,))
        receiverThread.start()

        # Start the UI
        Gtk.main()

        # Close the application if GTK quit
        logging.info("Closing the application...")
        self.client.shutdown(socket.SHUT_RDWR)
        self.client.close()
        logging.debug("Closed socket.")
        # Wait for the Receiver Thread
        logging.debug("Waiting for receiver thread to stop...")
        receiverThread.join()
        logging.debug("OK.")
        sys.exit(0)
