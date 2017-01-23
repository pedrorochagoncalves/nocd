import logging
import sys


class Packet(object):
    def __init__(self, operation, data=None):
        if operation is None:
            logging.critical("[FATAL] No operation specified while creating a packet. Exiting...")
            sys.exit(9)
        self.operation = operation
        self.data = data
