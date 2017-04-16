#!/usr/bin/python
import json
import logging
import nocpusher
import sys
import argparse
import nocdisplay
import fileEventHandler
import pyinotify


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
        parser.add_argument('--profile', dest='profile', action='store',
                            help='Sets the NOC profile. Select the dashboards to display.Ex: SRE or NET')
        parser.add_argument('--cycle-freq', dest='cycleFrequency', action='store', default=60,
                            help='Sets the dashboard cycle frequency. Defaults to 60 seconds.')
        args = parser.parse_args()

        if args.host and not args.profile and not args.cycleFrequency:
            parser.error("NOCDisplays requires NOC profile and cycle frequency. "
                         "Add --profile with SRE and --cycle-freq with 60 (s) for example.")
            sys.exit(1)

        # Start the app
        if args.server is True:
            noc = nocpusher.Nocpusher(config_file=args.config)
            # The watch manager stores the watches and provides operations on watches
            wm = pyinotify.WatchManager()
            mask = pyinotify.IN_MODIFY  # watched events
            file_event_handler = fileEventHandler.EventHandler(noc)
            notifier = pyinotify.ThreadedNotifier(wm, file_event_handler)
            # Start the notifier from a new thread, without doing anything as no directory or
            # file are currently monitored yet.
            notifier.start()
            # Start watching a path
            wdd = wm.add_watch(args.config, mask)
            # Run the server's main method
            noc.run()
            # Stop the notifier's thread
            notifier.stop()
        else:
            noc = nocdisplay.Nocdisplay(config_file=args.config, host=args.host, port=args.port, profile=args.profile,
                                        cycleFrequency=args.cycleFrequency)
            noc.run()

        sys.exit(0)
