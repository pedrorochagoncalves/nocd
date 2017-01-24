import logging
import socket
import time
import struct
import sys
import pickle
from common import Common
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.common.keys import Keys


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
        self.browser_profile = webdriver.FirefoxProfile(config['firefox_profile'])
        self.browser_profile.accept_untrusted_certs = True
        self.browsers = webdriver.Firefox(self.browser_profile)

    def set_dashboards(self, dashboards=None):
        self.dashboards = dashboards

    def run(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((self.host, self.port))

        # Prepare the Browsers. Window placement depends on the operation mode
        type(self.browsers)
        self.browsers.maximize_window()

        # Sleep a few seconds to give firefox time to maximize the window
        # I've seen firefox not have enough time to maximize and then the windows aren't properly sized
        time.sleep(5)
        logging.info("Starting NOCDisplay in Single DashBoard mode.")

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
                        self.browsers.get(self.dashboards[i])
                        try:
                            passwordInput = self.browsers.find_element_by_id("pass-signin")
                            userInput = self.browsers.find_element_by_id("user-signin")
                            if userInput is not None:
                                userInput.send_keys(self.user)
                                passwordInput.send_keys(self.password)
                                passwordInput.send_keys(Keys.RETURN)

                        except NoSuchElementException as msg:
                            logging.debug("No OKTA login found, proceeding.")
                        if i != len(self.dashboards) - 1:
                            self.browsers.execute_script("window.open('');")
                            self.browsers.switch_to_window(self.browsers.window_handles[-1])
                            self.browsers.maximize_window()

                elif p.operation == Common.SWITCH_TAB:
                    logging.debug("Switching window to %d: %s", p.data, self.dashboards[p.data])
                    self.browsers.switch_to_window(self.browsers.window_handles[p.data])
                    self.browsers.get(self.dashboards[p.data])
                    try:
                        self.browsers.execute_script('alert(1);')
                    except WebDriverException:
                        logging.debug("Switched window.")
                    alert = self.browsers.switch_to_alert()
                    alert.accept()

            except KeyboardInterrupt:
                self.client.close()
                sys.exit(3)
