import json
import logging
import nocanator
import argparse
import nocdisplay

logging.basicConfig(level=logging.DEBUG)

class App():

    # Main function that runs the actual Application
    if __name__ == '__main__':

        parser = argparse.ArgumentParser(description='NOCanator 3000 - Keeping OPS teams in Sync.')
        parser.add_argument('--config', dest='config', action='store', default='config.json',
                            help='Path to JSON config file.')
        parser.add_argument('-s', dest='server', action='store_true', default=False,
                            help='Sets the app to run as the server (the dashboard pusher). Defaults to False (client mode)')
        parser.add_argument('-a', dest='host', action='store',
                            help='Sets the server address for the Nocanator. Required if using client mode.')
        parser.add_argument('-p', dest='port', action='store', default=4455,
                            help='Sets the server port for the Nocanator. Defaults to port 4455.')
        args = parser.parse_args()

        # Open config file and load it into memory
        try:
            with open(args.config) as f:
                config = json.load(f)
        except IOError as msg:
            logging.critical('Cannot open config file: %s' % msg)
            exit(1)

        # Start the app
        if args.server is True:
            noc = nocanator.Nocanator(config)
            noc.run()
        else:
            noc = nocdisplay.Nocdisplay(host=args.host, port=args.port)
            noc.run()