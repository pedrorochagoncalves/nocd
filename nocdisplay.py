import logging
import socket
import sys
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys


class Nocdisplay(object):

    def __init__(self, host=None, port=4455):
        if host is None:
            logging.critical("No server address specified. Exiting...")
            sys.exit(2)
        else:
            self.host = host

        self.port = int(port)
        self.client = None
        self.browsers = []
        self.browsers.append(webdriver.Firefox())
        self.browsers.append(webdriver.Firefox())

    def run(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((self.host, self.port))

        # Prepare the Browsers. We want one window on the top and on on the bottom (vertical screens)
        type(self.browsers)
        self.browsers[0].maximize_window()
        windowSize = self.browsers[0].get_window_size()
        for i in range(0, len(self.browsers)):
            self.browsers[i].set_window_size(windowSize['width'], windowSize['height'] / 2)
        self.browsers[0].set_window_position(0, 0)
        self.browsers[1].set_window_position(0, windowSize['height'] / 2)

        running = True
        while running:
            try:
                dashBoards = self.client.recv(128)
                dashBoards = dashBoards.split(";")
                logging.debug("Received DashBoards: %s", dashBoards)
                logging.info("First Dashboard: %s", dashBoards[0])
                logging.info("Second Dashboard: %s",  dashBoards[1])

                # Open the dashboards in the browser but check if OKTA login
                #  is required.
                self.browsers[0].get(dashBoards[0])
                try:
                    passwordInput = self.browsers[0].find_element_by_id(
                        "pass-signin")
                    if passwordInput is not None:
                        passwordInput.send_keys("RulezPico368*")
                        passwordInput.send_keys(Keys.RETURN)

                except NoSuchElementException as msg:
                    logging.debug("No OKTA login found, proceeding.")

                self.browsers[1].get(dashBoards[1])
                try:
                    passwordInput = self.browsers[1].find_element_by_id(
                        "pass-signin")
                    if passwordInput is not None:
                        passwordInput.send_keys("RulezPico368*")
                        passwordInput.send_keys(Keys.RETURN)

                except NoSuchElementException as msg:
                    logging.debug("No OKTA login found, proceeding.")
            except KeyboardInterrupt:
                self.client.close()
                sys.exit(3)
