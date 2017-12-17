import logging
import random
import sys
import time
from gistapi import Gistapi
from pybrowser import Browser
import gi.repository
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit', '3.0')
from gi.repository import Gtk, WebKit, Gdk
from threading import Thread
from gi.repository import GObject

GObject.threads_init()
Gdk.threads_init()

class Nocd(object):

    def __init__(self, username=None, password=None, gist_config_url=None, profile=None, cycle_frequency=60):

        # Configure Logging
        logging.basicConfig(level=logging.DEBUG, filename='/dev/stdout')

        if not username or not password:
            logging.critical("OKTA username and password are required.")
            sys.exit(1)
        if not gist_config_url:
            logging.critical("Provided git repo URL is empty.")
            sys.exit(1)

        self.gist                 = Gistapi(gist_config_url)
        self.username             = username
        self.password             = password
        self.browser              = Browser(self.username, self.password)
        self.num_tabs             = 1
        self.client               = None
        self.profile              = profile
        self.cycle_frequency      = cycle_frequency
        self.run_cycle_tab_thread = True
        self.cycle_tab_thread     = None
        self.bind_window          = None
        self.dashboards           = self.gist.get_dashboards(profile)

    def init_browser(self):
        self.browser = Browser(self.username, self.password)

    def set_dashboards(self, dashboards=None):
        self.dashboards = dashboards

    def open_dashboards(self):
        """
        Open dashboards listed in self.dashboards that were pulled
        from git.
        """

        # Close all opened tabs
        for num_tabs in range(self.num_tabs):
            if self.num_tabs == 1:
                break
            GObject.idle_add(self.browser.close_tab)
            self.num_tabs -= 1

        # Open new tabs
        for num_tabs in range(len(self.dashboards) - 1):
            GObject.idle_add(self.browser.new_tab)
            self.num_tabs += 1

        # Open all dashboards
        for i in range(len(self.dashboards)):
            logging.debug("Opening {0} {1}.".format(self.dashboards[i], i))
            GObject.idle_add(self.browser.load_url_in_tab, i, self.dashboards[i])

        logging.debug("Opened %i tabs.", self.num_tabs)

    def cycle_tabs(self):
        """
        Cycles through the dashboards/tabs
        """
        while self.run_cycle_tab_thread:
            # Loop through dashboards-tabs
            for i in range(len(self.dashboards) - 1, -1, -1):
                for j in range(int(self.cycle_frequency)):
                    time.sleep(1)
                    if not self.run_cycle_tab_thread:
                        break
                logging.debug("Switching tabs to tab number %d: %s", i, self.dashboards[i])
                GObject.idle_add(self.browser.reload_url_in_tab, i, self.dashboards[i])

    def start_cycle_tab_thread(self):
        self.cycle_tab_thread = Thread(target=self.cycle_tabs)
        self.cycle_tab_thread.setDaemon(True)
        self.run_cycle_tab_thread = True
        self.cycle_tab_thread.start()

    def stop_cycle_tab_thread(self):
        self.run_cycle_tab_thread = False
        self.cycle_tab_thread.join()

    def clear_all_and_open_new_dashboard(self, url):

        # Stop cycling dashboards
        self.stop_cycle_tab_thread()

        # Close all tabs except first one
        for num_tabs in range(self.num_tabs-1):
            if self.num_tabs == 1:
                break
            GObject.idle_add(self.browser.close_tab)
            self.num_tabs -= 1
        del self.dashboards[:]

        # Open new dashboard
        GObject.idle_add(self.browser.load_url_in_tab, 0, url)
        # Add it to the list of dashboards
        self.dashboards.append(url)

        # Start cycling dashboards
        self.start_cycle_tab_thread()

    def add_dashboard(self, url):

        # Stop cycling dashboards
        self.stop_cycle_tab_thread()

        # Open new tab
        GObject.idle_add(self.browser.new_tab)
        self.num_tabs += 1

        # Load dashboard
        GObject.idle_add(self.browser.load_url_in_tab, self.num_tabs-1, url)
        # Add it to the list of dashboards
        self.dashboards.append(url)

        # Start cycling dashboards
        self.start_cycle_tab_thread()

    def close_tab(self, tab_index):

        # Check if index exists
        if tab_index+1 > self.num_tabs:
            return False
        # Check if last tab
        if tab_index == -1:
            tab_index = self.num_tabs - 1

        # Stop cycling dashboards
        self.stop_cycle_tab_thread()

        # Close tab
        GObject.idle_add(self.browser.close_tab, tab_index)
        self.num_tabs -= 1
        # Remove it from the list of dashboards
        del(self.dashboards[tab_index])

        # Start cycling dashboards
        self.start_cycle_tab_thread()

    def create_bind_window(self):
        """
        Creates a GTK window with a random int to bind a user to a NOCd instance
        :return: the random generated int
        """
        bind_number = random.randint(1, 10000)
        self.bind_window = Gtk.Window()
        label = Gtk.Label("<span size=\"400000\">" + str(bind_number) + "</span>")
        label.set_use_markup(True)
        self.bind_window.add(label)
        GObject.idle_add(self.bind_window.show_all)

        return bind_number

    def destroy_bind_window(self):
        """
        Destroys the GTK window created to show a random int and bind a user to a NOCd instance
        :return:
        """
        GObject.idle_add(self.bind_window.destroy)

    def open_dashboards_for_profile(self, profile=None):
        """
        Connects to the NOC server, sends the NOC profile and receives the dashboards
        :return: True if dashboards are received, False if not
        """

        # Stop cycling dashboards
        self.stop_cycle_tab_thread()

        if profile:
            self.profile = profile

        self.set_dashboards(self.gist.get_dashboards(self.profile))
        self.open_dashboards()

        # Start cycling dashboards
        self.start_cycle_tab_thread()

    def run(self):
        logging.info("Starting NOCd...")

        # Initialize the UI
        Gtk.init(sys.argv)

        # Dashboards were pulled in init
        self.open_dashboards()

        # Start cycling dashboards
        self.start_cycle_tab_thread()

        # Start the UI
        Gtk.main()

        # Close the application if GTK quit
        logging.info("Closing the application...")
        self.stop_cycle_tab_thread()
        logging.info("Bye.")

        # Exit
        return True
