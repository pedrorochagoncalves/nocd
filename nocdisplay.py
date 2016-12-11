import logging
import socket
import time
import struct
import sys
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys


class Nocdisplay(object):

    def __init__(self, config, host=None, port=4455):
        if host is None:
            logging.critical("No server address specified. Exiting...")
            sys.exit(2)
        else:
            self.host = host

        self.port = int(port)
        self.user = config['user']
        self.password = config['password']
        self.client = None
        self.browsers = []
        self.browser_profile = webdriver.FirefoxProfile(config['firefox_profile'])
        self.browser_profile.accept_untrusted_certs = True
        self.browsers.append(webdriver.Firefox(self.browser_profile))
        self.browsers.append(webdriver.Firefox(self.browser_profile))

    def run(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((self.host, self.port))

        # Prepare the Browsers. We want one window on the top and on on the bottom (vertical screens)
        type(self.browsers)
        self.browsers[0].maximize_window()
        # Sleep a few seconds to give firefox time to maximize the window
        # I've seen firefox not have enough time to maximize and then the windows aren't properly sized
        time.sleep(5)
        windowSize = self.browsers[0].get_window_size()
        for i in range(0, len(self.browsers)):
            self.browsers[i].set_window_size(windowSize['width'], windowSize['height'] / 2)
        self.browsers[0].set_window_position(0, 0)
        self.browsers[1].set_window_position(0, windowSize['height'] / 2)

        running = True
        while running:
            try:
                # Receive the size of the URLs packet first
                urlsPacketSizeByteString = self.client.recv(4)
                urlsPacketSize, = struct.unpack('!I', urlsPacketSizeByteString)
                # Now that we know how long the URLs are gonna be, we can receive them properly
                dashBoards = self.client.recv(urlsPacketSize)
                dashBoards = dashBoards.split(";")
                logging.debug("Received DashBoards: %s", dashBoards)
                logging.info("First Dashboard: %s", dashBoards[0])
                logging.info("Second Dashboard: %s",  dashBoards[1])

                # Open the dashboards in the browser but check if OKTA/Grafana
                # login is required.
                self.browsers[0].get(dashBoards[0])
                try:
                    passwordInput = self.browsers[0].find_element_by_id(
                        "pass-signin")
                    userInput = self.browsers[0].find_element_by_id(
                        "user-signin")
                    if userInput is not None:
                        userInput.send_keys(self.user)
                        passwordInput.send_keys(self.password)
                        passwordInput.send_keys(Keys.RETURN)

                except NoSuchElementException as msg:
                    logging.debug("No OKTA login found, proceeding.")

                self.browsers[1].get(dashBoards[1])
                try:
                    passwordInput = self.browsers[1].find_element_by_id(
                        "pass-signin")
                    userInput = self.browsers[1].find_element_by_id(
                        "user-signin")
                    if userInput is not None:
                        userInput.send_keys(self.user)
                        passwordInput.send_keys(self.password)
                        passwordInput.send_keys(Keys.RETURN)

                except NoSuchElementException as msg:
                    logging.debug("No OKTA login found, proceeding.")
            except KeyboardInterrupt:
                self.client.close()
                sys.exit(3)
