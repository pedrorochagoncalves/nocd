import logging
import socket
import struct
import sys
import pickle
import time
from common import Common
from pybrowser import Browser
import gi.repository
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit', '3.0')
from gi.repository import Gtk, WebKit
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
                # Now t hat we know how big the packet is going to be, we can receive it properly
                serializedPacket = self.client.recv(packetSize)
                p = pickle.loads(serializedPacket)
                logging.debug("Received packet with operation %d", p.operation)

                # Receive new list of dashboards
                if p.operation == Common.RECEIVE_DASHBOARDS:
                    self.set_dashboards(p.data)
                    # Open all dashboards
                    for i in range(len(self.dashboards)):
                        self.do_thread_work(self.load_url_in_tab, browser, i, self.dashboards[i])

                        if i != len(self.dashboards) - 1:
                            self.do_thread_work(self.new_tab, browser)

                elif p.operation == Common.SWITCH_TAB:
                    logging.debug("Switching window to %d: %s", p.data, self.dashboards[p.data])
                    self.do_thread_work(self.reload_and_focus_tab, browser, p.data)

            except:
                sys.exit(3)

    def load_url_in_tab(self, browser, tabIndex, url):
        browser.tabs[tabIndex][0].load_url(url)
        self.okta_login(browser, tabIndex)

    def new_tab(self, browser):
        browser.open_new_tab()

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
