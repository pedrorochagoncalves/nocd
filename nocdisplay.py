import logging
import socket
import time
import struct
import sys
from common import common
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys


class Nocdisplay(object):

    def __init__(self, config, mode=common.DUAL_DASHBOARD_MODE, host=None, port=4455):
        if host is None:
            logging.critical("No server address specified. Exiting...")
            sys.exit(2)
        else:
            self.host = host

        self.port = int(port)
        self.user = config['user']
        self.password = config['password']
        self.mode = mode
        self.client = None
        self.browsers = []
        self.browser_profile = webdriver.FirefoxProfile(config['firefox_profile'])
        self.browser_profile.accept_untrusted_certs = True
        self.browsers.append(webdriver.Firefox(self.browser_profile))
        # No need for two browsers if running in Single DashBoard mode
        if self.mode != common.SINGLE_DASHBOARD_MODE:
            self.browsers.append(webdriver.Firefox(self.browser_profile))

        # Get the static dashboard if Single Dashboard mode is selected
        if self.mode == common.SINGLE_STATIC_DASHBOARD_MODE:
            try:
                self.staticDashboard = config['static_dashboard']
            except:
                logging.critical("Single DashBoard with static dashboard mode selected, "
                                 "but no static dashboard provided in config file.")
                sys.exit(4)



    def run(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((self.host, self.port))

        # Prepare the Browsers. Window placement depends on the operation mode
        type(self.browsers)
        self.browsers[0].maximize_window()

        # Sleep a few seconds to give firefox time to maximize the window
        # I've seen firefox not have enough time to maximize and then the windows aren't properly sized
        time.sleep(5)

        # Check operation mode
        if self.mode == common.DUAL_DASHBOARD_MODE:
            windowSize = self.browsers[0].get_window_size()
            for i in range(0, len(self.browsers)):
                self.browsers[i].set_window_size(windowSize['width'], windowSize['height'] / 2)
            self.browsers[0].set_window_position(0, 0)
            self.browsers[1].set_window_position(0, windowSize['height'] / 2)
            logging.info("Starting NOCDisplay in Dual DashBoard mode.")
        elif self.mode == common.SINGLE_STATIC_DASHBOARD_MODE:
            windowSize = self.browsers[0].get_window_size()
            self.browsers[0].set_window_size(windowSize['width'], float(windowSize['height']) * 0.67)
            self.browsers[1].set_window_size(windowSize['width'], float(windowSize['height']) * 0.33)
            self.browsers[0].set_window_position(0, 0)
            self.browsers[1].set_window_position(0, float(windowSize['height']) * 0.67)
            logging.info("Starting NOCDisplay in Single DashBoard mode with additional an Static DashBoard.")
        else:
            logging.info("Starting NOCDisplay in Single DashBoard mode.")


        running = True
        while running:
            try:
                # Receive the size of the URLs packet first
                urlsPacketSizeByteString = self.client.recv(4)
                urlsPacketSize, = struct.unpack('!I', urlsPacketSizeByteString)
                # Now that we know how long the URLs are gonna be, we can receive them properly
                receivedDashBoards = self.client.recv(urlsPacketSize)
                logging.debug("Received DashBoards: %s", receivedDashBoards)
                if self.mode == common.DUAL_DASHBOARD_MODE:
                    dashBoards = receivedDashBoards.split(";")
                    logging.info("First Dashboard: %s", dashBoards[0])
                    logging.info("Second Dashboard: %s",  dashBoards[1])
                elif self.mode == common.SINGLE_STATIC_DASHBOARD_MODE:
                    dashBoards = list()
                    dashBoards.append(receivedDashBoards)
                    dashBoards.append(self.staticDashboard)
                else:
                    dashBoards = list()
                    dashBoards.append(receivedDashBoards)

                # Open the dashboards in the browser but check if OKTA/Grafana
                # login is required.
                for i in range(0, len(self.browsers)):
                    self.browsers[i].get(dashBoards[i])
                    try:
                        passwordInput = self.browsers[i].find_element_by_id(
                            "pass-signin")
                        userInput = self.browsers[i].find_element_by_id(
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
