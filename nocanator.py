import socket
import logging

class Nocanator(object):

    def __init__(self, config=None):
        if config is None:
            logging.critical("No config provided. Exiting...")
            exit(2)
        self.port = config['port']
        self.server = None

        try:
            if config['host'] is not None:
                self.host = config['host']
        except KeyError:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 53))
                self.host = s.getsockname()[0]
            except socket.error as msg:
                logging.critical('Unable to retrieve server\'s IP address: %s' % msg)
                exit(3)

        if config['dashboards'] is not None:
            self.dashboards = config['dashboards']
        else:
            logging.critical('No NOC Dashboards provided. Exiting...')
            exit(4)

    def open_socket(self):
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind((self.host, self.port))
            self.server.listen(8)
        except socket.error, (value, message):
            if self.server:
                self.server.close()
            logging.critical( "Could not open socket: " + message)
            exit(5)

    def run(self):
        logging.info("WELCOME TO THE NOCanator 3000\n")
        initMsg = "Initialized with IP " + self.host + ",port " + str(self.port) + " and the following dashboards:\n"
        for i in range(0, len(self.dashboards)):
            initMsg += self.dashboards[i] + "\n"
        logging.debug(initMsg)


