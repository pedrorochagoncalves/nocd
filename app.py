import json
import logging
import nocanator
import argparse

logging.basicConfig(level=logging.DEBUG)

class App():

    # Main function that runs the actual Application
    if __name__ == '__main__':

        parser = argparse.ArgumentParser(description='NOCanator 3000 - Keeping OPS teams in Sync.')
        parser.add_argument('--config', dest='config', action='store', default='config.json',
                            help='Path to JSON config file.')
        args = parser.parse_args()

        # Open config file and load it into memory
        try:
            with open(args.config) as f:
                config = json.load(f)
        except IOError as msg:
            logging.critical('Cannot open config file: %s' % msg)
            exit(1)

        # Start the app
        noc = nocanator.Nocanator(config)
        noc.run()