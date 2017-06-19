#!/usr/bin/env Python

import requests
import argparse
import json
import sys
from os.path import expanduser


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PyNOC-CLI - CLI tool to control the NOC displays.')
    parser.add_argument('--bind', dest='bind_address', action='store', default=False,
                        help='Hostname or IP to bind the CLI tool to.')
    parser.add_argument('-a', '--add_dashboard', dest='add_dashboard_url', action='store', default=False,
                        help='Adds a new dashboard to the current rotation')
    parser.add_argument('-d', '--del_dashboard', type=int, dest='del_dashboard_index', action='store', default=0,
                        help='Removes the specified dashboard by index. First tab (index 0) will not be removed. -1 '
                             'for the last tab.')
    parser.add_argument('--stop-cycle', dest='stop_cycle', action='store_true', default=False,
                        help='Stops the dashboard cycle.')
    parser.add_argument('--start-cycle', dest='start_cycle', action='store_true', default=False,
                        help='Sets the dashboard cycle frequency. Defaults to 60 seconds.')
    parser.add_argument('-p', '--profile', dest='profile', action='store', default=False,
                        help='Opens the dashboards for the specified profile. Ex: SRE, NET...')
    args = parser.parse_args()

    home_dir = expanduser("~")

    if args.bind_address:
        # Send the request to bind
        requests.get("http://{0}:5000/bind-noc-display-request".format(args.bind_address))

        # Loop until the correct number is typed in
        while True:
            # Wait for user to input the bind number displayed on the screen
            print 'Type the number displayed on the NOC display and press enter.'
            bind_number = raw_input('PyNOC-CLI> ')

            # Send the typed number
            print "You typed {0}. Let's give that a try.".format(bind_number)
            bind_req = requests.get("http://{0}:5000/bind-noc-display/te-{1}".format(args.bind_address, bind_number))

            # Check if we got a 401 or a 200
            if bind_req.status_code == 401:
                print('Hmm...401...looks like you did not type right number. Care to try again, if you please?')
            elif bind_req.status_code == 200:
                print('Yay we are bound now! Time to change the world!')
                with open("{0}/.pynoc-cli.conf".format(home_dir), 'wr') as conf_file:
                    conf = dict([('Token', bind_req.text), ('bind_address', args.bind_address)])
                    conf_file.write(json.dumps(conf))
                break

    elif args.add_dashboard_url:
        # Get token
        print('do stuff')


# Exit
sys.exit(0)
