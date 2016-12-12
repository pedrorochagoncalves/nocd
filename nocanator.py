#!/usr/bin/python
import json
import logging
import nocpusher
import sys
import argparse
import nocdisplay
from common import common

logging.basicConfig(level=logging.DEBUG)

class Nocanator():

    # Main function that runs the actual Application
    if __name__ == '__main__':

        parser = argparse.ArgumentParser(description='NOCanator 3000 - Keeping OPS teams in Sync.')
        parser.add_argument('--config', dest='config', action='store', default='config.json',
                            help='Path to JSON config file.')
        parser.add_argument('-s', dest='server', action='store_true', default=False,
                            help='Sets the app to run as the server (the dashboard pusher). Defaults to False (client mode)')
        parser.add_argument('-a', dest='host', action='store',
                            help='Sets the server address for the Nocpusher. Required if using client mode.')
        parser.add_argument('-p', dest='port', action='store', default=4455,
                            help='Sets the server port for the Nocpusher. Defaults to port 4455.')
        parser.add_argument('-m', dest='mode', action='store', default='dual',
                            help='Sets the operation mode. Available options are Dual Dashboard ( -m dual), '
                                 'Single DashBoard in full screen (-m single), and Single DashBoard with additional'
                                 'Static DashBoard (-m static). Defaults to Dual DashBoard. URL to Static DashBoard must be '
                                 'provided in config file (static_dashboard) if mode with Static DashBoard is to be selected.')
        args = parser.parse_args()

        # Open config file and load it into memory
        try:
            with open(args.config) as f:
                config = json.load(f)
        except IOError as msg:
            logging.critical('Cannot open config file: %s' % msg)
            sys.exit(1)

        # Handle the operation mode
        if args.mode == 'dual':
            mode = common.DUAL_DASHBOARD_MODE
        elif args.mode == 'single':
            mode = common.SINGLE_DASHBOARD_MODE
        elif args.mode == 'static':
            mode = common.SINGLE_STATIC_DASHBOARD_MODE
        else:
            logging.critical("Unknown operation mode. Must be either 'dual', 'single' or 'static'. Exiting.")
            sys.exit(1)

        # Start the app
        if args.server is True:
            noc = nocpusher.Nocpusher(config=config, mode=mode)
            noc.run()
        else:
            noc = nocdisplay.Nocdisplay(config=config, mode=mode, host=args.host, port=args.port)
            noc.run()
