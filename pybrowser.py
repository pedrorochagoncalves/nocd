# Original author: https://gist.github.com/kklimonda/890640

import gi.repository
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit', '3.0')
from gi.repository import Gtk, Gdk, WebKit
import json
import requests
import time

class BrowserTab(Gtk.VBox):
    def __init__(self, username, password, *args, **kwargs):
        super(BrowserTab, self).__init__(*args, **kwargs)

        self.webview = WebKit.WebView()
        self.show()

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.add(self.webview)

        find_box = Gtk.HBox()
        close_button = Gtk.Button("Close")
        close_button.connect("clicked", lambda x: find_box.hide())
        self.find_entry = Gtk.Entry()
        self.find_entry.connect("activate",
                                lambda x: self.webview.search_text(self.find_entry.get_text(),
                                                                   False, True, True))

        find_box.pack_start(close_button, False, False, 0)
        find_box.pack_start(self.find_entry, False, False, 0)
        self.find_box = find_box

        self.pack_start(scrolled_window, True, True, 0)
        self.pack_start(find_box, False, False, 0)

        self.username = username
        self.password = password

        scrolled_window.show_all()

    def load_url(self, url):
        if "://" not in url:
            url = "http://" + url
        self.webview.load_uri(url)
        time.sleep(2)
        if self.needs_okta_login():
            self.log_in_to_okta(url)

    def reload_tab(self, url):
        if "://" not in url:
            url = "http://" + url
        self.webview.reload()
        time.sleep(2)
        if self.needs_okta_login():
            self.log_in_to_okta(url)

    def get_html(self):
        self.webview.execute_script('oldtitle=document.title;document.title=document.documentElement.innerHTML;')
        html = self.webview.get_main_frame().get_title()
        self.webview.execute_script('document.title=oldtitle;')
        return html

    def get_url(self):
        url = self.webview.get_uri()
        print url
        return url

    def get_okta_session_token(self):
        headers = {"Accept": "application/json", "content-Type": "application/json"}
        data = json.dumps({
            "username": self.username,
            "password": self.password,
            "options": {
                "multiOptionalFactorEnroll": False,
                "warnBeforePasswordExpired": False
            }
        })
        reply = requests.post('https://thousandeyes.okta.com/api/v1/authn', data=data, headers=headers)
        okta_auth_reply = reply.json()

        return okta_auth_reply['sessionToken']

    def log_in_to_okta(self, url):
        session_token = self.get_okta_session_token()
        self.webview.load_uri(
            "https://thousandeyes.okta.com/login/sessionCookieRedirect?token={0}&redirectUrl={1}".format(session_token,
                                                                                                         url))
    def needs_okta_login(self):
        tab_url = self.get_url()
        if tab_url and 'okta.com/login/login.htm' in tab_url:
            return True
        else:
            return False


class Browser(Gtk.Window):
    def __init__(self, username, password, *args, **kwargs):
        super(Browser, self).__init__(*args, **kwargs)

        # OKTA credentials
        self.username = username
        self.password = password

        # create notebook and tabs
        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)

        # basic stuff
        self.tabs = []
        self.fullscreen()

        # create a first, empty browser tab
        self.tabs.append((self._create_tab(), Gtk.Label("New Tab")))
        self.notebook.append_page(*self.tabs[0])
        self.add(self.notebook)

        # connect signals
        self.connect("destroy", Gtk.main_quit)
        self.connect("key-press-event", self._key_pressed)
        self.notebook.connect("switch-page", self._tab_changed)

        self.notebook.show()
        self.show()

    def _tab_changed(self, notebook, current_page, index):
        if not index:
            return
        title = self.tabs[index][0].webview.get_title()
        if title:
            self.set_title(title)

    def focus_tab(self, index):
        self.notebook.get_nth_page(index)

    def _title_changed(self, webview, frame, title):
        current_page = self.notebook.get_current_page()

        counter = 0
        for tab, label in self.tabs:
            if tab.webview is webview:
                label.set_text(title)
                if counter == current_page:
                    self._tab_changed(None, None, counter)
                break
            counter += 1

    def _create_tab(self):
        tab = BrowserTab(self.username, self.password)
        tab.webview.connect("title-changed", self._title_changed)
        return tab

    def _reload_and_focus_tab(self, tab_index, url):
        self.tabs[tab_index][0].reload_tab(url)
        time.sleep(5)
        self.notebook.set_current_page(tab_index)

    def _close_current_tab(self):
        if self.notebook.get_n_pages() == 1:
            return
        page = self.notebook.get_current_page()
        current_tab = self.tabs.pop(page)
        self.notebook.remove(current_tab[0])

    def _open_new_tab(self):
        # Get the last tab
        last_page = self.notebook.get_n_pages()
        page_tuple = (self._create_tab(), Gtk.Label("New Tab"))
        self.tabs.insert(last_page + 1, page_tuple)
        self.notebook.insert_page(page_tuple[0], page_tuple[1], last_page + 1)
        self.notebook.set_current_page(last_page + 1)

    def _focus_url_bar(self):
        current_page = self.notebook.get_current_page()
        self.tabs[current_page][0].url_bar.grab_focus()

    def _raise_find_dialog(self):
        current_page = self.notebook.get_current_page()
        self.tabs[current_page][0].find_box.show_all()
        self.tabs[current_page][0].find_entry.grab_focus()

    def _key_pressed(self, widget, event):
        modifiers = Gtk.accelerator_get_default_mod_mask()
        mapping = {Gdk.KEY_w: self._close_current_tab,
                   Gdk.KEY_t: self._open_new_tab,
                   Gdk.KEY_l: self._focus_url_bar,
                   Gdk.KEY_f: self._raise_find_dialog,
                   Gdk.KEY_q: Gtk.main_quit}

        if event.state & modifiers == Gdk.ModifierType.CONTROL_MASK \
                and event.keyval in mapping:
            mapping[event.keyval]()

    def load_url_in_tab(self, tab_index, url):
        self.tabs[tab_index][0].load_url(url)

    def reload_url_in_tab(self, tab_index, url):
        self._reload_and_focus_tab(tab_index, url)

    def new_tab(self):
        self._open_new_tab()

    def close_tab(self):
        self._close_current_tab()
