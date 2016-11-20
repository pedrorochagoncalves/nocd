import logging
import socket
import sys
from selenium import webdriver

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
                print (dashBoards)
                print("First Dashboard: %s" % dashBoards[0])
                print("Second Dashboard: %s" % dashBoards[1])
                self.browsers[0].get(dashBoards[0])
                self.browsers[1].get(dashBoards[1])
            except KeyboardInterrupt:
                self.client.close()
                sys.exit(3)
