import logging
import socket
import time
import struct
import sys
import pickle
from common import Common
from pybrowser import Browser
import gi.repository
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from threading import Thread
from gi.repository import GObject

class Nocdisplay(object):

    def __init__(self, config, host=None, port=4455):
        if host is None:
            logging.critical("FATAL: No server address specified. Exiting...")
            sys.exit(2)
        else:
            self.host = host

        self.port = int(port)
        self.user = config['user']
        self.password = config['password']
        self.dashboards = None
        self.client = None

    def set_dashboards(self, dashboards=None):
        self.dashboards = dashboards

    def receiverProcessor(self, browser):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((self.host, self.port))

        running = True
        while running:
            try:
                # Receive the size of the packet first
                packetSizeByteString = self.client.recv(4)
                packetSize, = struct.unpack('!I', packetSizeByteString)
                # Now that we know how big the packet is going to be, we can receive it properly
                serializedPacket = self.client.recv(packetSize)
                p = pickle.loads(serializedPacket)
                logging.debug("Received packet with operation %d", p.operation)

                # Receive new list of dashboards
                if p.operation == Common.RECEIVE_DASHBOARDS:
                    self.set_dashboards(p.data)
                    print(self.dashboards[0])
                    # Open all dashboards
                    for i in range(len(self.dashboards)):
                        browser.tabs[i][0].load_url(self.dashboards[i])

                        if i != len(self.dashboards) - 1:
                            browser.open_new_tab()

                elif p.operation == Common.SWITCH_TAB:
                    logging.debug("Switching window to %d: %s", p.data, self.dashboards[p.data])
                    browser.focus_tab(p.data)

            except KeyboardInterrupt:
                self.client.close()
                sys.exit(3)

    def load_url_in_tab(self, browser, tabIndex, url):
        browser.tabs[tabIndex][0].load_url(url)

    def new_tab(self, browser):
        browser.open_new_tab()

    def focus_tab(self, browser, tabIndex):
        browser.notebook.set_current_page(tabIndex)

    def do_thread_work(self, function, *args):
        GObject.idle_add(function, *args)

    #def stop_thread_work(self):


    def run(self):
        logging.info("Starting NOCDisplay...")

        # Create the Browser
        #packetQueue = Queue()
        Gtk.init(sys.argv)
        browser = Browser()


        # Start the Receiver Processor Thread
        testThread = Thread(target=self.do_thread_work, args=(self.load_url_in_tab, browser, 0, 'www.google.com'))
        testThread.start()

        testThread2 = Thread(target=self.do_thread_work, args=(self.new_tab, browser,))
        testThread2.start()

        testThread3 = Thread(target=self.do_thread_work, args=(self.load_url_in_tab, browser, 1, 'www.apple.com'))
        testThread3.start()

        testThread4 = Thread(target=self.do_thread_work, args=(self.focus_tab, browser, 0,))
        testThread4.start()

        # Start the UI
        Gtk.main()

        # Wait for the Receiver Thread
        #receiverThread.join()
